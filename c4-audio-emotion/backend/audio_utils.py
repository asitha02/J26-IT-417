"""
Audio helpers: YouTube URL checking, video info, downloading and cutting audio.

Pipeline: download_complete_audio() -> cut_segments()
          (first 3 min as numbers)     (10 s windows, 5 s hop)

Two ways to download (download_complete_audio tries them in this order):
  1. download_audio_fast(): asks YouTube's server for only the first few MB of the
     audio file in one normal HTTP request (~3 s).
  2. download_audio(): lets ffmpeg stream the first 3 minutes (~90 s, because YouTube
     limits streaming speed). Slower, but works for every format: the fallback.
"""
import logging
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import librosa
import numpy as np
import requests
import yt_dlp
from yt_dlp.utils import download_range_func

from backend.config import HOP_SECONDS, MAX_AUDIO_SECONDS, SAMPLE_RATE, SEGMENT_SECONDS

logger = logging.getLogger("c4.audio")

# A YouTube video id is always 11 characters: letters, digits, "-" or "_".
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


class VideoUnavailableError(Exception):
    """The video could not be read (private, deleted, wrong id, no internet...)."""


def extract_video_id(url: str):
    """
    Return the 11-character video id from a YouTube URL, or None if it isn't one.

    Accepted forms:
      https://www.youtube.com/watch?v=ID
      https://youtu.be/ID
      https://www.youtube.com/shorts/ID
    """
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    path_parts = [p for p in parsed.path.split("/") if p]

    video_id = None
    if host == "youtu.be" and path_parts:
        video_id = path_parts[0]
    elif host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        elif len(path_parts) == 2 and path_parts[0] == "shorts":
            video_id = path_parts[1]

    if video_id and VIDEO_ID_PATTERN.match(video_id):
        return video_id
    return None


_info_cache = {}           # video_id -> (time fetched, yt-dlp info); YouTube's audio links stay valid for hours
INFO_CACHE_SECONDS = 300


def _youtube_info(video_id: str) -> dict:
    """
    Ask YouTube once for the video's details AND its audio formats, and reuse the answer for
    5 minutes. get_video_info() and download_audio_fast() both need it (saves ~2.5 s per analysis).
    Raises yt_dlp DownloadError if the video can't be read.
    """
    cached = _info_cache.get(video_id)
    if cached and time.time() - cached[0] < INFO_CACHE_SECONDS:
        return cached[1]
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "format": "bestaudio"}) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    _info_cache[video_id] = (time.time(), info)
    return info


def get_video_info(video_id: str) -> dict:
    """Read the title and duration from YouTube without downloading anything."""
    try:
        info = _youtube_info(video_id)
    except yt_dlp.utils.DownloadError as e:
        raise VideoUnavailableError(str(e)) from e

    if not info.get("duration"):
        # Live streams have no fixed length, so we can't take "the first 3 minutes".
        raise VideoUnavailableError("Live streams or videos without a duration are not supported.")
    return {"title": info.get("title", ""), "duration": float(info["duration"])}


def make_segment_times(total_seconds: float) -> list[dict]:
    """
    Split [0, total_seconds] into overlapping windows of SEGMENT_SECONDS,
    starting every HOP_SECONDS. Only the first MAX_AUDIO_SECONDS are used.

    Example (180 s): 0-10, 5-15, 10-20, ..., 170-180  -> 35 windows.
    A last window that would run past the end is still included; its
    missing audio is padded with silence on Day 5. Audio shorter than one
    window gives a single window 0-total.
    """
    total = min(total_seconds, MAX_AUDIO_SECONDS)
    if total <= SEGMENT_SECONDS:
        return [{"start_s": 0, "end_s": round(total, 2)}]

    segments = []
    start = 0
    while start + SEGMENT_SECONDS < total:
        segments.append({"start_s": start, "end_s": start + SEGMENT_SECONDS})
        start += HOP_SECONDS
    # Final window: ends exactly at the end of the audio (may be shorter than 10 s).
    segments.append({"start_s": start, "end_s": round(total, 2)})
    return segments


class AudioDownloadError(Exception):
    """yt-dlp or ffmpeg could not download / convert the audio."""


def download_audio(video_id: str, out_dir: str) -> Path:
    """
    Download ONLY the first MAX_AUDIO_SECONDS of the video's audio track
    and convert it to a WAV file inside out_dir. Returns the WAV path.

    Downloading just the first 3 minutes (not the whole video) keeps
    long videos fast. ffmpeg does the cutting and the WAV conversion.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    options = {
        "format": "bestaudio/best",                     # audio only, no video
        "outtmpl": str(Path(out_dir) / f"{video_id}.%(ext)s"),
        "download_ranges": download_range_func(None, [(0, MAX_AUDIO_SECONDS)]),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        # -nostdin: ffmpeg must not read keyboard input from the terminal the server runs in;
        # otherwise typing in that terminal during a download can interrupt ffmpeg.
        "external_downloader_args": {"ffmpeg_i": ["-nostdin"]},
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        raise AudioDownloadError(f"Download failed: {e}") from e

    wav_path = Path(out_dir) / f"{video_id}.wav"
    if not wav_path.exists():
        raise AudioDownloadError("Download finished but no WAV file was produced (is ffmpeg installed?).")
    return wav_path


def download_audio_fast(video_id: str, out_dir: str) -> Path:
    """
    Fast download: request only the first bytes of the audio file (an HTTP "Range" request),
    roughly enough for MAX_AUDIO_SECONDS plus a safety margin, then let ffmpeg convert
    that piece to a 48 kHz mono WAV of at most MAX_AUDIO_SECONDS. Returns the WAV path.
    Raises AudioDownloadError if anything is missing, so the caller can fall back.
    """
    try:
        info = _youtube_info(video_id)
    except yt_dlp.utils.DownloadError as e:
        raise AudioDownloadError(f"Could not read the audio formats: {e}") from e

    fmt = info["requested_formats"][0] if info.get("requested_formats") else info
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    duration = info.get("duration")
    if not fmt.get("url") or fmt.get("protocol") not in ("https", "http") or not size or not duration:
        raise AudioDownloadError("Fast download not possible for this video's audio format.")

    # Bytes for the first MAX_AUDIO_SECONDS (+5 s), +10 % and +200 kB margin because the bitrate varies.
    share = min(1.0, (MAX_AUDIO_SECONDS + 5) / duration)
    n_bytes = min(int(size), int(size * share * 1.1) + 200_000)
    headers = {**fmt.get("http_headers", {}), "Range": f"bytes=0-{n_bytes - 1}"}
    try:
        response = requests.get(fmt["url"], headers=headers, timeout=60)
        response.raise_for_status()
    except requests.RequestException as e:
        raise AudioDownloadError(f"Fast download failed: {e}") from e

    part_path = Path(out_dir) / f"{video_id}.{fmt.get('ext', 'audio')}"
    part_path.write_bytes(response.content)
    wav_path = Path(out_dir) / f"{video_id}.wav"
    # -nostdin: don't read keyboard input; -t: keep at most MAX_AUDIO_SECONDS; -ac 1 -ar: mono, 48 kHz
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(part_path),
         "-t", str(MAX_AUDIO_SECONDS), "-ac", "1", "-ar", str(SAMPLE_RATE), str(wav_path)],
        capture_output=True, text=True,
    )
    part_path.unlink(missing_ok=True)
    if result.returncode != 0 or not wav_path.exists():
        raise AudioDownloadError(f"ffmpeg could not convert the downloaded audio: {result.stderr[-200:]}")
    return wav_path


def load_audio(path) -> np.ndarray:
    """
    Read an audio file as numbers: one float per sample, 48 000 per second, mono.
    librosa resamples to SAMPLE_RATE and mixes stereo down to mono for us.
    Only the first MAX_AUDIO_SECONDS are kept.
    """
    audio, _ = librosa.load(path, sr=SAMPLE_RATE, mono=True, duration=MAX_AUDIO_SECONDS)
    return audio


def cut_segments(audio: np.ndarray) -> list[dict]:
    """
    Cut the audio into the windows from make_segment_times().
    Every window is exactly SEGMENT_SECONDS long: a shorter last window is
    padded with silence (zeros) so the model always gets the same input size.

    Returns [{'start_s', 'end_s', 'audio': np.ndarray of SEGMENT_SECONDS * SAMPLE_RATE}, ...]
    """
    window_len = SEGMENT_SECONDS * SAMPLE_RATE
    segments = []
    for times in make_segment_times(len(audio) / SAMPLE_RATE):
        start = int(times["start_s"] * SAMPLE_RATE)
        chunk = audio[start:start + window_len]
        if len(chunk) < window_len:
            chunk = np.pad(chunk, (0, window_len - len(chunk)))  # add silence at the end
        segments.append({**times, "audio": chunk})
    return segments


def download_complete_audio(video_id: str, out_dir: str, video_duration: float, attempts: int = 3) -> np.ndarray:
    """
    Download + load the audio, and CHECK it is complete: we expect
    min(video length, MAX_AUDIO_SECONDS) seconds.

    Attempt 1 uses the fast method; if it fails or is incomplete, the remaining attempts use
    the slower ffmpeg streaming method. A dropped internet connection can make a download
    fail (ffmpeg crashes) or stop early without any error; both are retried, up to
    `attempts` times in total. If it still fails, raise a clear error instead of
    silently analysing part of the video.
    """
    expected = min(video_duration, MAX_AUDIO_SECONDS)
    methods = [download_audio_fast] + [download_audio] * (attempts - 1)
    problem = ""
    for attempt, method in enumerate(methods, start=1):
        for f in Path(out_dir).glob(f"{video_id}.*"):
            f.unlink()                     # remove any partial file from a previous attempt
        try:
            audio = load_audio(method(video_id, out_dir))
        except AudioDownloadError as e:
            problem = str(e)
            logger.warning("Download attempt %d/%d (%s) for %s failed: %s", attempt, attempts, method.__name__, video_id, e)
            continue
        got = len(audio) / SAMPLE_RATE
        if got >= expected - 2:           # allow 2 s tolerance for rounding
            return audio
        problem = f"only {got:.0f} s of the expected {expected:.0f} s were downloaded"
        logger.warning("Download attempt %d/%d for %s incomplete: %s", attempt, attempts, video_id, problem)
    raise AudioDownloadError(f"Download failed after {attempts} attempts ({problem}). "
                             "The internet connection may be unstable. Please try again.")
