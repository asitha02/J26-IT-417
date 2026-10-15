"""
Audio helpers: YouTube URL checking, video info, downloading and cutting audio.

Pipeline: download_audio() -> load_audio() -> cut_segments()
          (WAV file)          (numbers)       (10 s windows, 5 s hop)
"""
import logging
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import librosa
import numpy as np
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


def get_video_info(video_id: str) -> dict:
    """Read the title and duration from YouTube without downloading anything."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(url, download=False)
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
