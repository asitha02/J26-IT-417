"""
C4 FastAPI backend: two parts (CLAUDE.md section 8.6).

  Part 1  Affective Audio Analysis           POST /audio/analyze, GET /audio/analyses[/{video_id}]
  Part 2  Content Enhancement Recommendations POST /recommendations/{video_id}, GET /recommendations/{video_id}

Start it from the c4-audio-emotion folder:
    venv\\Scripts\\python -m uvicorn backend.main:app --reload
Then open http://localhost:8000/docs to try the endpoints.
"""
import logging
import tempfile

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from backend import db
from backend.audio_analysis import run_audio_analysis
from backend.audio_utils import (
    AudioDownloadError,
    VideoUnavailableError,
    download_complete_audio,
    extract_video_id,
    get_video_info,
)
from backend.config import AUDIO_ANALYSES_COLLECTION, MODEL_PATH, USE_MOCK_MODEL, USE_SOURCE_SEPARATION
from backend.model import get_model
from backend.schemas import AnalyzeRequest, AudioAnalysisResponse, Summary
from backend.separation import get_separator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("c4")

app = FastAPI(title="C4 Audio Emotion API")
# Loaded once at start-up and reused for every request (loading takes several seconds).
emotion_model = get_model(USE_MOCK_MODEL, MODEL_PATH)
separator = get_separator(USE_SOURCE_SEPARATION)


@app.exception_handler(PyMongoError)
def database_error(request: Request, exc: PyMongoError):
    """Any MongoDB problem -> a clear 503 error instead of a crash."""
    logger.exception("Database error")
    return JSONResponse(status_code=503, content={"detail": "Database unavailable. Check MONGODB_URI and network access."})


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Part 1: Affective Audio Analysis ----------

@app.post("/audio/analyze", response_model=AudioAnalysisResponse)
def audio_analyze(request: AnalyzeRequest):
    # 1. Validate the URL and get the video id.
    video_id = extract_video_id(request.youtube_url)
    if video_id is None:
        raise HTTPException(status_code=400, detail="Not a valid YouTube URL (use a watch, youtu.be or shorts link).")

    # 2. Reuse the saved result unless the user asked to re-analyse.
    if not request.force_reanalyze:
        cached = db.get(video_id, AUDIO_ANALYSES_COLLECTION)
        if cached is not None:
            logger.info("Returning cached audio analysis for %s", video_id)
            return cached

    # 3. Read title and duration from YouTube.
    try:
        info = get_video_info(video_id)
    except VideoUnavailableError as e:
        logger.warning("Video %s unavailable: %s", video_id, e)
        raise HTTPException(status_code=422, detail=f"Could not read this video: {e}")

    # 4. Download the first 3 minutes of audio (temporary files are deleted automatically).
    try:
        with tempfile.TemporaryDirectory() as tmp:
            audio = download_complete_audio(video_id, tmp, info["duration"])
    except AudioDownloadError as e:
        logger.error("Audio download failed for %s: %s", video_id, e)
        raise HTTPException(status_code=502, detail=f"Could not download the audio: {e}")

    # 5. Separate, predict emotion, measure problems, describe the music (backend/audio_analysis.py).
    analysis = run_audio_analysis(video_id, info["title"], audio, emotion_model, separator)

    # 6. Save (replaces any older analysis of the same video) and return.
    db.save(analysis, AUDIO_ANALYSES_COLLECTION)
    logger.info("Audio analysis done for %s (%d windows, separation=%s, %d problems)", video_id,
                len(analysis["segments"]), analysis["separation"]["method"], len(analysis["audio_problems"]))
    return db.get(video_id, AUDIO_ANALYSES_COLLECTION)


@app.get("/audio/analyses", response_model=list[Summary])
def list_audio_analyses():
    return db.list_summaries(AUDIO_ANALYSES_COLLECTION)


@app.get("/audio/analyses/{video_id}", response_model=AudioAnalysisResponse)
def get_audio_analysis(video_id: str):
    analysis = db.get(video_id, AUDIO_ANALYSES_COLLECTION)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"No audio analysis saved for video '{video_id}'.")
    return analysis
