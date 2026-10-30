"""
Real check: download a video, separate speech from background music with Demucs, print loudness.

Run from the c4-audio-emotion folder (first run downloads the ~80 MB Demucs model):
    venv\Scripts\python -m scripts.test_separation "https://www.youtube.com/watch?v=VIDEO_ID"
"""
import sys
import tempfile
import time

import numpy as np

from backend.audio_utils import download_complete_audio, extract_video_id, get_video_info
from backend.separation import Separator

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=e-P5IFTqB98"
video_id = extract_video_id(url)
with tempfile.TemporaryDirectory() as tmp:
    audio = download_complete_audio(video_id, tmp, get_video_info(video_id)["duration"])

t0 = time.time()
separator = Separator()
print(f"1. Demucs loaded in {time.time() - t0:.0f} s")
t0 = time.time()
speech, background = separator.separate(audio)
print(f"2. Separated {len(audio) / 48000:.0f} s of audio in {time.time() - t0:.0f} s")

db = lambda a: 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-9)    # loudness in dB (0 = maximum)
print(f"3. Loudness: mixed {db(audio):.1f} dB | speech {db(speech):.1f} dB | background {db(background):.1f} dB")
print(f"   -> background music is {db(speech) - db(background):.1f} dB quieter than the narration")
