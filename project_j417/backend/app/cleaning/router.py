import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.cleaning import cleaner as cleaner_store
from app.cleaning import training
from app.cleaning.pipeline import REASONS, clean_documents
from app.config import Settings, get_settings
from app.transcription.repository import Repository

router = APIRouter(prefix="/api/cleaning", tags=["cleaning"])


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


def cleaned_json(docs: list[dict], settings: Settings) -> dict:
    """The cleaned JSON of the given transcripts, using whatever trained models passed their tests."""
    return clean_documents(docs, cleaner_store.load_cleaner(settings.data_dir), cleaner_store.load_report(settings.data_dir))


async def _build(repo: Repository, settings: Settings) -> dict:
    docs = await repo.list_transcripts()
    if not docs:
        raise HTTPException(404, "No videos yet - add a video first.")
    return await asyncio.to_thread(cleaned_json, docs, settings)


@router.get("/summary")
async def summary(repo: Repository = Depends(get_repo), settings: Settings = Depends(get_settings)):
    """Quality numbers only (no segment text): totals, per-video quality, and examples of what was removed."""
    out = await _build(repo, settings)
    return {
        "generated_at": out["generated_at"],
        "cleaning": {k: v for k, v in out["cleaning"].items() if k != "model_test_results"},
        "reasons": REASONS,
        "summary": out["summary"],
        "videos": [{k: v[k] for k in ("source_id", "title", "source_url", "duration_sec", "quality")} for v in out["videos"]],
        "removed_examples": out["removed_examples"],
    }


@router.get("/download")
async def download(repo: Repository = Depends(get_repo), settings: Settings = Depends(get_settings)):
    """One cleaned JSON containing every video."""
    out = await _build(repo, settings)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return Response(
        json.dumps(out, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="cleaned-transcripts-{stamp}.json"'},
    )


@router.get("/model")
async def model_info(settings: Settings = Depends(get_settings)):
    """The test results of the trained cleaning models (if trained) and which jobs they now do."""
    report = cleaner_store.load_report(settings.data_dir)
    return {"report": report, "in_use": cleaner_store.load_cleaner(settings.data_dir).in_use}


@router.post("/train")
async def train(repo: Repository = Depends(get_repo), settings: Settings = Depends(get_settings)):
    """Train the three cleaning models on the stored transcripts, test each on data it never saw, and use the ones that pass."""
    docs = await repo.list_transcripts()
    if not docs:
        raise HTTPException(404, "No videos yet - add a video first.")
    try:
        sentences, words, duplicates, report = await asyncio.to_thread(training.train_all, docs)
    except training.TrainingError as exc:
        raise HTTPException(422, str(exc)) from exc
    cleaner_store.save(settings.data_dir, sentences, words, duplicates, report)
    return {"report": report, "in_use": cleaner_store.load_cleaner(settings.data_dir).in_use}
