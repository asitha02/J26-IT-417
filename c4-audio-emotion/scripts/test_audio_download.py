"""
Day 5 check: download a real video's audio, load it, and cut it into windows.

Run from the c4-audio-emotion folder:
    venv\\Scripts\\python -m scripts.test_audio_download "https://www.youtube.com/watch?v=VIDEO_ID"
"""
import sys
import tempfile
import time

from backend.audio_utils import cut_segments, download_audio, extract_video_id, load_audio
from backend.config import SAMPLE_RATE

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=jNQXAC9IVRw"
video_id = extract_video_id(url)
assert video_id, f"Not a valid YouTube URL: {url}"

# TemporaryDirectory deletes the folder (and the WAV inside it) when the block ends.
with tempfile.TemporaryDirectory() as tmp:
    t0 = time.time()
    wav = download_audio(video_id, tmp)
    print(f"1. Downloaded {wav.name} ({wav.stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.1f} s")

    audio = load_audio(wav)
    print(f"2. Loaded {len(audio)} samples = {len(audio) / SAMPLE_RATE:.1f} s at {SAMPLE_RATE} Hz, mono")

    segments = cut_segments(audio)
    print(f"3. Cut into {len(segments)} windows:")
    for i, s in enumerate(segments):
        # Print the first 3 and the last window only.
        if i < 3 or i == len(segments) - 1:
            print(f"   {s['start_s']:>5}-{s['end_s']:<6} s  audio shape {s['audio'].shape}")
        elif i == 3:
            print("   ...")

print("4. Temporary audio deleted. Done.")
