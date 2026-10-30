"""The list of transcribed videos, each video's cleaned JSON, and removing a video."""

import asyncio
import json
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from app.cleaning.data import latest_per_video
from app.cleaning.router import cleaned_json
from app.config import Settings, get_settings
from app.transcription.repository import Repository

router = APIRouter(prefix="/api/videos", tags=["videos"])

_SAFE_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,119}$")


class VideoOut(BaseModel):
    source_id: str
    title: str | None = None
    source_url: str
    uploader: str | None = None
    duration_sec: float | None = None
    language: str | None = None
    asr_model: str | None = None
    segments: int


class DeleteOut(BaseModel):
    source_id: str
    transcripts_removed: int
    jobs_removed: int


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


@router.get("", response_model=list[VideoOut])
async def list_videos(repo: Repository = Depends(get_repo)):
    docs = sorted(latest_per_video(await repo.list_transcripts()), key=lambda d: str(d.get("created_at", "")), reverse=True)
    return [
        VideoOut(
            source_id=d["source_id"],
            title=d.get("title"),
            source_url=d["source_url"],
            uploader=d.get("uploader"),
            duration_sec=d.get("duration_sec"),
            language=d.get("language"),
            asr_model=d.get("asr_model"),
            segments=len(d.get("segments", [])),
        )
        for d in docs
    ]


@router.get("/{source_id}/download")
async def download_cleaned_video(
    source_id: str, repo: Repository = Depends(get_repo), settings: Settings = Depends(get_settings)
):
    """One video's cleaned JSON: redundant sentences, error words and duplicates removed, timestamps kept."""
    if not _SAFE_ID.match(source_id):
        raise HTTPException(400, "Invalid video id.")
    docs = latest_per_video(await repo.list_transcripts([source_id]))
    if not docs:
        raise HTTPException(404, "That video is not in your list.")
    cleaned = await asyncio.to_thread(cleaned_json, docs, settings)
    return Response(
        json.dumps(cleaned, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{source_id}-cleaned.json"'},
    )


@router.delete("/{source_id}", response_model=DeleteOut)
async def delete_video(source_id: str, repo: Repository = Depends(get_repo), settings: Settings = Depends(get_settings)):
    """Remove a video everywhere: its transcript, its jobs and the saved JSON file."""
    if not _SAFE_ID.match(source_id):
        raise HTTPException(400, "Invalid video id.")
    removed = await repo.delete_video(source_id)
    if removed["transcripts"] == 0:
        raise HTTPException(404, "That video is not in your list.")
    (settings.transcript_dir / f"{source_id}.json").unlink(missing_ok=True)
    return DeleteOut(source_id=source_id, transcripts_removed=removed["transcripts"], jobs_removed=removed["jobs"])
