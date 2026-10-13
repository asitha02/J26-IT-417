"""
Audio helpers: YouTube URL checking, video info, and segment timing.

Day 3: URL validation, metadata (title, duration) and segment start/end times.
Day 5 adds: downloading the audio, converting to WAV, trimming and cutting it.
"""
import re
from urllib.parse import parse_qs, urlparse

import yt_dlp

from backend.config import HOP_SECONDS, MAX_AUDIO_SECONDS, SEGMENT_SECONDS

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
