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

# --- Audio processing constants (see CLAUDE.md section 9.1) ---
SEGMENT_SECONDS = 10     # length of each analysis window
HOP_SECONDS = 5          # step between window starts (windows overlap by 5 s)
MAX_AUDIO_SECONDS = 180  # only the first 3 minutes are analysed
