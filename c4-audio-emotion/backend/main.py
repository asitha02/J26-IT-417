"""
C4 FastAPI backend: two parts (CLAUDE.md section 8.6).

  Part 1  Affective Audio Analysis           POST /audio/analyze, GET /audio/analyses[/{video_id}]
  Part 2  Content Enhancement Recommendations POST /recommendations/{video_id}, GET /recommendations/{video_id}

Start it from the c4-audio-emotion folder:
    venv\\Scripts\\python -m uvicorn backend.main:app --reload
Then open http://localhost:8000/docs to try the endpoints.

Part 1 answers in two phases: a quick "first look" on the mixed audio (~10 s, status "processing"),
then Demucs separation in the background (~1.5 min) replaces it with the full result (status "complete").
"""
import logging
import tempfile
import threading
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
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
from backend.config import (
    AUDIO_ANALYSES_COLLECTION,
    MODEL_PATH,
    RECOMMENDATIONS_COLLECTION,
    USE_MOCK_MODEL,
    USE_SOURCE_SEPARATION,
)
from backend.mock_loader import load_c1_transcript, load_c3_sentiment, load_knowledge_gaps
from backend.model import get_model
from backend.report import build_report
from backend.schemas import AnalyzeRequest, AudioAnalysisResponse, RecommendationReport, Summary
from backend.separation import NoSeparation, get_separator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("c4")

app = FastAPI(title="C4 Audio Emotion API")
# Loaded once at start-up and reused for every request (loading takes several seconds).
emotion_model = get_model(USE_MOCK_MODEL, MODEL_PATH)
separator = get_separator(USE_SOURCE_SEPARATION)
separation_lock = threading.Lock()     # one Demucs run at a time
STALE_PROCESSING_SECONDS = 600         # a 'processing' result older than this is assumed lost (e.g. server restart)


@app.exception_handler(PyMongoError)
def database_error(request: Request, exc: PyMongoError):
    """Any MongoDB problem -> a clear 503 error instead of a crash."""
    logger.exception("Database error")
    return JSONResponse(status_code=503, content={"detail": "Database unavailable. Check MONGODB_URI and network access."})


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Part 1: Affective Audio Analysis ----------

def _is_fresh(doc: dict) -> bool:
    """A cached result is reusable if it is complete, or still being refined (started < 10 min ago)."""
    if doc.get("status") == "complete":
        return True
    if doc.get("status") == "processing":
        age = datetime.now(timezone.utc) - datetime.fromisoformat(doc["created_at"])
        return age.total_seconds() < STALE_PROCESSING_SECONDS
    return False                               # "failed": try again


def _refine_in_background(video_id: str, title: str, audio, created_at: str, mixed_preds) -> None:
    """
    Phase 2 (runs after the response was sent): separate voice and music with Demucs (~1.5 min on CPU),
    redo the analysis on the music track and replace the quick result. One separation at a time,
    so two requests don't fight over the CPU.
    """
    try:
        report_progress = lambda fraction: db.update(video_id, {"progress": round(fraction, 2)})
        with separation_lock:
            analysis = run_audio_analysis(video_id, title, audio, emotion_model, separator,
                                          mixed_preds=mixed_preds, on_progress=report_progress)
        analysis["created_at"] = created_at        # keep the original request time
        db.save(analysis, AUDIO_ANALYSES_COLLECTION)
        logger.info("Refined analysis done for %s (%d problems)", video_id, len(analysis["audio_problems"]))
    except Exception as e:                          # log it and tell the UI instead of failing silently
        logger.exception("Background separation failed for %s", video_id)
        doc = db.get(video_id, AUDIO_ANALYSES_COLLECTION) or {}
        doc.update({"status": "failed", "error": f"Separating voice and music failed: {e}"})
        db.save(doc, AUDIO_ANALYSES_COLLECTION)


@app.post("/audio/analyze", response_model=AudioAnalysisResponse)
def audio_analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    # 1. Validate the URL and get the video id.
    video_id = extract_video_id(request.youtube_url)
    if video_id is None:
        raise HTTPException(status_code=400, detail="Not a valid YouTube URL (use a watch, youtu.be or shorts link).")

    # 2. Reuse the saved result unless the user asked to re-analyse.
    if not request.force_reanalyze:
        cached = db.get(video_id, AUDIO_ANALYSES_COLLECTION)
        if cached is not None and _is_fresh(cached):
            logger.info("Returning cached audio analysis for %s (%s)", video_id, cached["status"])
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

    # 5. Phase 1, "first look" (~10 s): analyse the mixed audio without separation and answer straight away.
    analysis = run_audio_analysis(video_id, info["title"], audio, emotion_model, NoSeparation())
    if USE_SOURCE_SEPARATION:
        # Phase 2 runs in the background; the page polls GET /audio/analyses/{id} until status is "complete".
        analysis["status"] = "processing"
        analysis["progress"] = 0.0
        analysis["separation"]["method"] = "pending"
        mixed_preds = [{k: s[k] for k in ("start_s", "end_s", "valence", "arousal")} for s in analysis["segments"]]
        background_tasks.add_task(_refine_in_background, video_id, info["title"], audio,
                                  analysis["created_at"], mixed_preds)

    # 6. Save (replaces any older analysis of the same video) and return.
    db.save(analysis, AUDIO_ANALYSES_COLLECTION)
    logger.info("First look for %s ready (%d windows, status=%s)", video_id, len(analysis["segments"]), analysis["status"])
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


# ---------- Part 2: Content Enhancement Recommendations ----------

@app.post("/recommendations/{video_id}", response_model=RecommendationReport)
def create_recommendations(video_id: str):
    """Fuse the saved Part 1 result with the C1, C2 and C3 outputs (dummy for now). Fast: no audio work."""
    analysis = db.get(video_id, AUDIO_ANALYSES_COLLECTION)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Run Part 1 (audio analysis) for this video first.")
    if analysis.get("status") != "complete":
        raise HTTPException(status_code=409, detail="Part 1 is still separating voice and music for this video. "
                                                    "Please try again in a minute.")
    report = build_report(analysis, load_c1_transcript(video_id), load_knowledge_gaps(video_id),
                          load_c3_sentiment(video_id))
    db.save(report, RECOMMENDATIONS_COLLECTION)
    logger.info("Recommendations for %s: %d recommendations, validation lift=%s", video_id,
                len(report["recommendations"]), report["validation"]["lift"])
    return db.get(video_id, RECOMMENDATIONS_COLLECTION)


@app.get("/recommendations", response_model=list[Summary])
def list_recommendations():
    return db.list_summaries(RECOMMENDATIONS_COLLECTION)


@app.get("/recommendations/{video_id}", response_model=RecommendationReport)
def get_recommendations(video_id: str):
    report = db.get(video_id, RECOMMENDATIONS_COLLECTION)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No recommendations saved for video '{video_id}'.")
    return report
