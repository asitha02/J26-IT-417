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
#
# RELATIVE thresholds (changed 18 Oct): R1, R2 and R4 compare each window with THIS video's own
# average, not with fixed values. Reason: on speech + music science videos the model's predictions
# stay near neutral (arousal roughly -0.1..+0.2), so fixed thresholds like -0.3 never triggered.
# A section is "low energy" when it is clearly calmer than the rest of the same video, which is
# also how a viewer experiences pacing.
RELATIVE_DELTA = 0.04        # how far (in valence/arousal units) a window must be from the video average
R1_MIN_DURATION_S = 30       # R1 "low energy": arousal < average - delta for at least this long
R2_MIN_DURATION_S = 20       # R2 "tense": arousal > average + delta AND valence < average - delta, this long
R3_MIN_AROUSAL_STD = 0.03    # R3 "flat": arousal standard deviation over the clip below this
R3_MIN_WINDOWS = 6           # R3 needs at least 6 windows (35 s) to judge variety
NEGATIVE_SENTIMENT = -0.3    # a C3 comment / overall score below this counts as negative
COMMENT_WINDOW_S = 15        # a comment within ±15 s of a section counts as "about" that section
AUDIO_KEYWORDS = ["music", "loud", "volume", "audio", "boring", "slow"]

# --- Confidence scoring (0..1) ---
BASE_CONFIDENCE = 0.5        # one source of evidence (e.g. audio only)
CORROBORATION_BONUS = 0.2    # added for each independent signal that agrees (comment, gap)
MAX_CONFIDENCE = 0.95        # never claim certainty
