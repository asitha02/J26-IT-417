"""Audio extraction with yt-dlp.

Speed trick: we download the audio-only stream and hand it straight to
faster-whisper (which decodes + resamples to 16 kHz via PyAV), so there is no
separate ffmpeg conversion pass.
"""

import ipaddress
import re
import socket
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from yt_dlp.utils import DownloadError as YtDlpDownloadError

_YT_ID = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})")


class DownloadError(Exception):
    pass


class TooLongError(DownloadError):
    pass


@dataclass
class AudioResult:
    path: Path
    source_id: str
    title: str | None
    uploader: str | None
    duration: float | None
    webpage_url: str


def youtube_id(url: str) -> str | None:
    m = _YT_ID.search(url)
    return m.group(1) if m else None


def validate_url(url: str) -> None:
    """Reject non-http(s) URLs and anything pointing at local/private addresses (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Enter a valid http(s) URL.")
    host = parsed.hostname
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("Local addresses are not allowed.")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return  # let yt-dlp report unresolved hosts
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Private network addresses are not allowed.")


def _safe_id(extractor: str, vid: str) -> str:
    raw = vid if extractor.lower() == "youtube" else f"{extractor.lower()}-{vid}"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", raw)[:120]


def download_audio(
    url: str, out_dir: Path, max_duration: int, cookies_file: str | None = None
) -> AudioResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        # ASR does not need hi-fi: a ~128 kbps stream downloads fast and transcribes the same.
        "format": "bestaudio[abr<=130]/bestaudio/best",
        "outtmpl": str(out_dir / "%(extractor)s_%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "concurrent_fragment_downloads": 4,
        "restrictfilenames": True,
    }
    if cookies_file:
        opts["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                raise DownloadError("Playlists are not supported - paste a single video URL.")
            if info.get("is_live"):
                raise DownloadError("Live streams are not supported.")
            duration = info.get("duration")
            if duration and duration > max_duration:
                raise TooLongError(
                    f"Media is {duration / 3600:.1f} h long; the limit is {max_duration / 3600:.1f} h."
                )
            info = ydl.process_ie_result(info, download=True)
            downloads = info.get("requested_downloads") or []
            path = Path(downloads[0]["filepath"]) if downloads else Path(ydl.prepare_filename(info))
    except YtDlpDownloadError as exc:
        raise DownloadError(re.sub(r"\x1b\[[0-9;]*m", "", str(exc)).strip()) from exc

    if not path.exists():
        raise DownloadError("Audio download finished but the file is missing.")

    extractor = info.get("extractor_key") or info.get("extractor") or "web"
    return AudioResult(
        path=path,
        source_id=_safe_id(extractor, str(info["id"])),
        title=info.get("title"),
        uploader=info.get("uploader") or info.get("channel"),
        duration=float(duration) if (duration := info.get("duration")) else None,
        webpage_url=info.get("webpage_url") or url,
    )
