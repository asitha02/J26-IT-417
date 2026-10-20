"""
Day 2 check: can yt-dlp reach YouTube and read a video's details?

This only reads metadata (title, length); it does not download audio yet.
Downloading + converting to WAV needs ffmpeg and is built on Day 5.

Run from the c4-audio-emotion folder:
    venv\\Scripts\\python -m scripts.test_ytdlp "https://www.youtube.com/watch?v=VIDEO_ID"
"""
import shutil
import sys

import yt_dlp

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=jNQXAC9IVRw"

print(f"Reading video info for: {url}")
with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
    info = ydl.extract_info(url, download=False)  # download=False -> metadata only

print(f"  video_id : {info['id']}")
print(f"  title    : {info['title']}")
print(f"  duration : {info['duration']} s")

# ffmpeg is a separate program (not a Python package) that yt-dlp uses to make WAV files.
if shutil.which("ffmpeg"):
    print("ffmpeg   : found")
else:
    print("ffmpeg   : NOT found (needed from Day 5 to convert audio to WAV)")
