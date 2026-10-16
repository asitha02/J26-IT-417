"""
Central settings for the C4 backend.

Secrets (like the MongoDB connection string) come from the .env file,
so they are never written in the code or pushed to GitHub.
Fixed constants (segment length, etc.) live here so every module uses the same values.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load the .env file from the c4-audio-emotion folder (one level above backend/),
# no matter which folder the program is started from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- MongoDB (shared team Atlas database) ---
MONGODB_URI = os.getenv("MONGODB_URI")  # secret: never print this
MONGODB_DB = os.getenv("MONGODB_DB", "project_j417")
ANALYSES_COLLECTION = "analyses"

# --- Emotion model ---
# "true" (default) = fake MockEmotionModel; "false" = real trained model (Day 10)
USE_MOCK_MODEL = os.getenv("USE_MOCK_MODEL", "true").lower() == "true"
# Relative paths are taken from the c4-audio-emotion folder, whatever folder uvicorn is started from.
MODEL_PATH = PROJECT_ROOT / os.getenv("MODEL_PATH", "models/c4_emotion_head.pt")

# --- Audio processing constants (see CLAUDE.md section 9.1) ---
SEGMENT_SECONDS = 10     # length of each analysis window
HOP_SECONDS = 5          # step between window starts (windows overlap by 5 s)
MAX_AUDIO_SECONDS = 180  # only the first 3 minutes are analysed
SAMPLE_RATE = 48000      # samples per second; CLAP expects 48 kHz mono audio

# --- Dummy inputs from other components (replaced by real C3 / knowledge-graph output later) ---
MOCK_DATA_DIR = PROJECT_ROOT / "mock_data"

# --- Fusion rule thresholds (CLAUDE.md section 10) ---
# These are starting values to tune later, not proven truths.
R1_LOW_AROUSAL = -0.3        # arousal below this counts as "low energy"
R1_MIN_DURATION_S = 30       # low energy must last at least this long to be reported
R2_HIGH_AROUSAL = 0.6        # R2 "tense audio": arousal above this ...
R2_LOW_VALENCE = -0.3        # ... AND valence below this ...
R2_MIN_DURATION_S = 20       # ... for at least this long
R3_MIN_AROUSAL_VARIANCE = 0.01   # arousal variance below this = "flat" energy over the whole clip
R4_INTENSE_AROUSAL = 0.4     # arousal above this during a knowledge gap = intense audio over hard content
NEGATIVE_SENTIMENT = -0.3    # a C3 comment / overall score below this counts as negative
COMMENT_WINDOW_S = 15        # a comment within ±15 s of a section counts as "about" that section
AUDIO_KEYWORDS = ["music", "loud", "volume", "audio", "boring", "slow"]

# --- Confidence scoring (0..1) ---
BASE_CONFIDENCE = 0.5        # one source of evidence (e.g. audio only)
CORROBORATION_BONUS = 0.2    # added for each independent signal that agrees (comment, gap)
MAX_CONFIDENCE = 0.95        # never claim certainty
