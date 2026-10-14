import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

from app.config import Settings, get_settings
from app.transcription.downloader import validate_url, youtube_id
from app.transcription.repository import Repository
from app.transcription.schemas import JobOut, TranscriptCreate, TranscriptOut
from app.transcription.service import run_job
from app.transcription.transcriber import Transcriber

router = APIRouter(prefix="/api/transcripts", tags=["transcription"])


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


def get_transcriber(request: Request) -> Transcriber:
    return request.app.state.transcriber


def _job_out(job: dict) -> JobOut:
    return JobOut.model_validate({**job, "job_id": job["_id"]})


@router.post("", response_model=JobOut, status_code=202)
async def create_transcript_job(
    body: TranscriptCreate,
    background: BackgroundTasks,
    repo: Repository = Depends(get_repo),
    transcriber: Transcriber = Depends(get_transcriber),
    settings: Settings = Depends(get_settings),
):
    try:
        validate_url(body.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

    # Instant path: a YouTube video we already transcribed with this model.
    vid = youtube_id(body.url)
    if vid and not body.language:
        cached = await repo.find_cached(vid, transcriber.cfg.model, body.word_timestamps)
        if cached:
            job = await repo.create_job(
                body.url,
                status="done",
                progress=1.0,
                cached=True,
                source_id=cached["source_id"],
                title=cached.get("title"),
                duration_sec=cached.get("duration_sec"),
                transcript_id=cached["_id"],
            )
            return _job_out(job)

    job = await repo.create_job(body.url)
    background.add_task(
        run_job,
        job["_id"],
        body.url,
        body.language,
        body.word_timestamps,
        repo,
        transcriber,
        settings,
    )
    return _job_out(job)


@router.get("", response_model=list[JobOut])
async def list_jobs(limit: int = 20, repo: Repository = Depends(get_repo)):
    return [_job_out(j) for j in await repo.list_jobs(min(max(limit, 1), 100))]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: str, repo: Repository = Depends(get_repo)):
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_out(job)


async def _load_transcript(job_id: str, repo: Repository) -> TranscriptOut:
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] != "done":
        raise HTTPException(409, f"Transcript not ready (status: {job['status']})")
    doc = await repo.get_transcript(job["transcript_id"])
    if not doc:
        raise HTTPException(404, "Transcript not found")
    return TranscriptOut.model_validate(doc)


@router.get("/{job_id}/result", response_model=TranscriptOut, response_model_exclude_none=True)
async def get_result(job_id: str, repo: Repository = Depends(get_repo)):
    return await _load_transcript(job_id, repo)


@router.get("/{job_id}/download")
async def download_result(job_id: str, repo: Repository = Depends(get_repo)):
    transcript = await _load_transcript(job_id, repo)
    payload = json.dumps(
        transcript.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2
    )
    return Response(
        payload,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{transcript.source_id}.json"'},
    )
