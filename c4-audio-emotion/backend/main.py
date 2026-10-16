"""
C4 FastAPI backend.

Start it from the c4-audio-emotion folder:
    venv\\Scripts\\python -m uvicorn backend.main:app --reload
Then open http://localhost:8000/docs to try the endpoints.
"""
import logging
import tempfile
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError

from backend import db
from backend.audio_utils import (
    AudioDownloadError,
    VideoUnavailableError,
    cut_segments,
    download_complete_audio,
    extract_video_id,
    get_video_info,
)
from backend.config import HOP_SECONDS, MODEL_PATH, SAMPLE_RATE, SEGMENT_SECONDS, USE_MOCK_MODEL
from backend.fusion import generate_recommendations
from backend.mock_loader import load_c3_sentiment, load_knowledge_gaps
from backend.model import get_model, quadrant_of, summarize
from backend.schemas import AnalysisResponse, AnalysisSummary, AnalyzeRequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("c4")

app = FastAPI(title="C4 Audio Emotion API")
emotion_model = get_model(USE_MOCK_MODEL, MODEL_PATH)  # loaded once at start-up, reused for every request


@app.exception_handler(PyMongoError)
def database_error(request: Request, exc: PyMongoError):
    """Any MongoDB problem -> a clear 503 error instead of a crash."""
    logger.exception("Database error")
    return JSONResponse(status_code=503, content={"detail": "Database unavailable. Check MONGODB_URI and network access."})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResponse)
def analyze(request: AnalyzeRequest):
    # 1. Validate the URL and get the video id.
    video_id = extract_video_id(request.youtube_url)
    if video_id is None:
        raise HTTPException(status_code=400, detail="Not a valid YouTube URL (use a watch, youtu.be or shorts link).")

    # 2. Reuse the saved result unless the user asked to re-analyse.
    if not request.force_reanalyze:
        cached = db.get_analysis(video_id)
        if cached is not None:
            logger.info("Returning cached analysis for %s", video_id)
            return cached

    # 3. Read title and duration from YouTube.
    try:
        info = get_video_info(video_id)
    except VideoUnavailableError as e:
        logger.warning("Video %s unavailable: %s", video_id, e)
        raise HTTPException(status_code=422, detail=f"Could not read this video: {e}")

    # 4. Download the first 3 minutes of audio and cut it into windows.
    #    TemporaryDirectory deletes the WAV file automatically when the block ends.
    try:
        with tempfile.TemporaryDirectory() as tmp:
            audio = download_complete_audio(video_id, tmp, info["duration"])
    except AudioDownloadError as e:
        logger.error("Audio download failed for %s: %s", video_id, e)
        raise HTTPException(status_code=502, detail=f"Could not download the audio: {e}")
    segments_audio = cut_segments(audio)

    # 5. Predict valence/arousal for each window.
    predictions = emotion_model.predict(segments_audio, video_id=video_id)
    segments = [{**p, "quadrant": quadrant_of(p["valence"], p["arousal"])} for p in predictions]

    # 6. Load the (dummy) inputs from other components and apply the fusion rules.
    c3_input = load_c3_sentiment(video_id)
    gaps_input = load_knowledge_gaps(video_id)
    analyzed_seconds = round(len(audio) / SAMPLE_RATE, 2)

    analysis = {
        "video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "title": info["title"],
        "analyzed_seconds": analyzed_seconds,
        "segment_seconds": SEGMENT_SECONDS,
        "hop_seconds": HOP_SECONDS,
        "model_info": emotion_model.info,
        "segments": segments,
        "overall": summarize(segments),
        "c3_input": c3_input,       # DUMMY C3 sentiment ("mock": true)
        "gaps_input": gaps_input,   # DUMMY knowledge gaps ("mock": true)
        "recommendations": generate_recommendations(segments, c3_input, gaps_input, analyzed_seconds),
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 7. Save (replaces any older analysis of the same video) and return.
    db.save_analysis(analysis)
    logger.info("Analysed %s (%d segments, mock=%s)", video_id, len(segments), emotion_model.info["mock"])
    return db.get_analysis(video_id)


@app.get("/analyses", response_model=list[AnalysisSummary])
def list_analyses():
    return db.list_analyses()


@app.get("/analyses/{video_id}", response_model=AnalysisResponse)
def get_analysis(video_id: str):
    analysis = db.get_analysis(video_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail=f"No saved analysis for video '{video_id}'.")
    return analysis
