"""Job pipeline: download the audio of a link -> transcribe -> store JSON (Mongo + file)."""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone

from app.config import Settings
from app.transcription import downloader
from app.transcription.downloader import AudioResult, DownloadError, download_audio
from app.transcription.repository import Repository, transcript_key
from app.transcription.schemas import TranscriptOut
from app.transcription.transcriber import Transcriber

log = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None


def _gate(limit: int) -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(limit)
    return _semaphore


def _write_json_file(settings: Settings, doc: dict) -> None:
    settings.transcript_dir.mkdir(parents=True, exist_ok=True)
    payload = TranscriptOut.model_validate(doc).model_dump(mode="json")
    path = settings.transcript_dir / f"{doc['source_id']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def _transcribe_and_store(
    job_id: str,
    audio: AudioResult,
    language: str | None,
    word_timestamps: bool,
    repo: Repository,
    transcriber: Transcriber,
    settings: Settings,
    started: float,
) -> None:
    # Same media + same model already transcribed? Reuse it instantly.
    cached = await repo.find_cached(audio.source_id, transcriber.cfg.model, word_timestamps)
    if cached and not language:
        await repo.update_job(
            job_id,
            status="done",
            progress=1.0,
            cached=True,
            source_id=audio.source_id,
            title=audio.title,
            duration_sec=audio.duration,
            transcript_id=cached["_id"],
        )
        return

    await repo.update_job(
        job_id,
        status="transcribing",
        progress=0.1,
        source_id=audio.source_id,
        title=audio.title,
        duration_sec=audio.duration,
    )

    loop = asyncio.get_running_loop()
    last = {"p": 0.1}

    def on_progress(frac: float) -> None:
        p = round(0.1 + 0.88 * frac, 2)
        if p - last["p"] >= 0.02:  # throttle DB writes
            last["p"] = p
            asyncio.run_coroutine_threadsafe(repo.update_job(job_id, progress=p), loop)

    segments, meta = await asyncio.to_thread(
        transcriber.transcribe, audio.path, language, word_timestamps, on_progress
    )

    elapsed = round(time.perf_counter() - started, 2)
    doc = {
        "schema_version": "1.0",
        "source_id": audio.source_id,
        "source_url": audio.webpage_url,
        "title": audio.title,
        "uploader": audio.uploader,
        "duration_sec": audio.duration or meta["duration"],
        "language": meta["language"],
        "language_probability": meta["language_probability"],
        "asr_model": transcriber.cfg.model,
        "device": transcriber.cfg.device,
        "created_at": datetime.now(timezone.utc),
        "processing_time_sec": elapsed,
        "full_text": " ".join(s["text"] for s in segments),
        "segments": segments,
        "has_words": word_timestamps,
    }
    tid = await repo.save_transcript(doc)
    await asyncio.to_thread(_write_json_file, settings, doc)
    await repo.update_job(job_id, status="done", progress=1.0, transcript_id=tid, processing_time_sec=elapsed)


async def _guarded(job_id: str, repo: Repository, work) -> None:
    """Run one job step; any failure ends up on the job instead of crashing the server."""
    try:
        await work()
    except (DownloadError, ValueError) as exc:
        await repo.update_job(job_id, status="failed", error=str(exc))
    except Exception as exc:  # noqa: BLE001 - surface any ASR/IO failure on the job
        log.exception("Transcription job %s failed", job_id)
        await repo.update_job(job_id, status="failed", error=f"{type(exc).__name__}: {exc}")


async def run_job(
    job_id: str,
    url: str,
    language: str | None,
    word_timestamps: bool,
    repo: Repository,
    transcriber: Transcriber,
    settings: Settings,
) -> None:
    """A link: download its audio, then transcribe."""
    audio: AudioResult | None = None

    async def work() -> None:
        nonlocal audio
        started = time.perf_counter()
        await repo.update_job(job_id, status="downloading", progress=0.02)
        audio = await asyncio.to_thread(
            download_audio, url, settings.audio_dir, settings.max_duration_sec, settings.ytdlp_cookies_file
        )
        await _transcribe_and_store(job_id, audio, language, word_timestamps, repo, transcriber, settings, started)

    async with _gate(settings.max_concurrent_jobs):
        try:
            await _guarded(job_id, repo, work)
        finally:
            if audio is not None and not settings.keep_audio:
                audio.path.unlink(missing_ok=True)


__all__ = ["run_job", "transcript_key", "downloader"]
