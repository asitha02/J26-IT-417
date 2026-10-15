"""
Day 6 check: real video -> audio windows -> CLAP embeddings. Verifies the shape is (windows, 512).

Run from the c4-audio-emotion folder (first run downloads the ~600 MB CLAP model):
    venv\\Scripts\\python -m scripts.test_clap_embeddings "https://www.youtube.com/watch?v=VIDEO_ID"
"""
import sys
import tempfile
import time

import numpy as np

from backend.audio_utils import cut_segments, download_audio, extract_video_id, load_audio
from backend.model import ClapEmbedder

url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=jNQXAC9IVRw"
video_id = extract_video_id(url)
assert video_id, f"Not a valid YouTube URL: {url}"

with tempfile.TemporaryDirectory() as tmp:
    segments = cut_segments(load_audio(download_audio(video_id, tmp)))
print(f"1. Audio cut into {len(segments)} windows")

t0 = time.time()
embedder = ClapEmbedder()
print(f"2. CLAP loaded in {time.time() - t0:.1f} s")

t0 = time.time()
emb = embedder.embed(segments)
print(f"3. Embeddings computed in {time.time() - t0:.1f} s")

print(f"   shape: {emb.shape}   (expected: ({len(segments)}, 512))")
print(f"   first window, first 5 numbers: {np.round(emb[0, :5], 3)}")
print(f"   vector lengths (CLAP normalises them to 1.0): {np.round(np.linalg.norm(emb, axis=1)[:3], 3)}")
if len(emb) > 1:
    # Cosine similarity: 1.0 = identical sound, ~0 = unrelated.
    print(f"   similarity window 0 vs 1 (overlapping): {emb[0] @ emb[1]:.3f}")
    print(f"   similarity window 0 vs last:            {emb[0] @ emb[-1]:.3f}")

assert emb.shape == (len(segments), 512), "Unexpected embedding shape!"
print("\nCLAP embedding check passed.")
