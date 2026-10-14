"""End-to-end API test with the heavy parts (yt-dlp, Whisper, MongoDB) replaced by fakes."""

import copy
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import AsrConfig, Settings
from app.main import create_app
from app.transcription import service
from app.transcription.downloader import AudioResult, DownloadError, validate_url
from app.transcription.repository import transcript_key


class FakeRepo:
    def __init__(self):
        self.jobs, self.transcripts = {}, {}

    async def create_job(self, url, **extra):
        now = datetime.now(timezone.utc)
        job = {"_id": uuid.uuid4().hex, "status": "queued", "progress": 0.0, "source_url": url,
               "cached": False, "created_at": now, "updated_at": now, **extra}
        self.jobs[job["_id"]] = job
        return copy.deepcopy(job)

    async def update_job(self, job_id, **fields):
        self.jobs[job_id].update(fields)

    async def get_job(self, job_id):
        return copy.deepcopy(self.jobs.get(job_id))

    async def list_jobs(self, limit=20):
        return list(self.jobs.values())[:limit]

    async def get_transcript(self, tid):
        return copy.deepcopy(self.transcripts.get(tid))

    async def find_cached(self, source_id, model, need_words):
        doc = self.transcripts.get(transcript_key(source_id, model))
        return None if (doc is None or (need_words and not doc.get("has_words"))) else doc

    async def save_transcript(self, doc):
        tid = transcript_key(doc["source_id"], doc["asr_model"])
        self.transcripts[tid] = {**doc, "_id": tid}
        return tid


class FakeTranscriber:
    cfg = AsrConfig("fake-model", "cpu", "int8", 8, 5)
    calls = 0

    def transcribe(self, path, language=None, word_timestamps=False, on_progress=None):
        FakeTranscriber.calls += 1
        if on_progress:
            on_progress(0.5)
        segs = [
            {"id": 0, "start": 0.0, "end": 2.5, "text": "Hello world.", "confidence": 0.95},
            {"id": 1, "start": 2.5, "end": 5.0, "text": "Second segment.", "confidence": 0.9},
        ]
        return segs, {"language": "en", "language_probability": 0.99, "duration": 5.0}


@pytest.fixture
def client(tmp_path, monkeypatch):
    settings = Settings(data_dir=tmp_path, keep_audio=False)
    monkeypatch.setattr("app.transcription.router.get_settings", lambda: settings, raising=False)

    def fake_download(url, out_dir, max_duration, cookies=None):
        if "bad" in url:
            raise DownloadError("Video unavailable")
        out_dir.mkdir(parents=True, exist_ok=True)
        p = Path(out_dir) / "youtube_dQw4w9WgXcQ.m4a"
        p.write_bytes(b"x")
        return AudioResult(p, "dQw4w9WgXcQ", "Test video", "Tester", 5.0, url)

    monkeypatch.setattr(service, "download_audio", fake_download)
    FakeTranscriber.calls = 0
    app = create_app()
    app.state.repo, app.state.transcriber = FakeRepo(), FakeTranscriber()
    app.dependency_overrides[__import__("app.config", fromlist=["x"]).get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c, tmp_path


YT = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_full_flow_then_cache(client):
    c, tmp = client
    r = c.post("/api/transcripts", json={"url": YT})
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    job = c.get(f"/api/transcripts/{job_id}").json()
    assert job["status"] == "done" and job["progress"] == 1.0

    result = c.get(f"/api/transcripts/{job_id}/result").json()
    assert result["source_id"] == "dQw4w9WgXcQ"
    assert result["segments"][1]["start"] == 2.5
    assert result["full_text"] == "Hello world. Second segment."
    assert (tmp / "transcripts" / "dQw4w9WgXcQ.json").exists()
    assert not list((tmp / "audio").glob("*"))  # audio cleaned up

    dl = c.get(f"/api/transcripts/{job_id}/download")
    assert "attachment" in dl.headers["content-disposition"]

    # Second request for the same video is served from cache, no new ASR run.
    r2 = c.post("/api/transcripts", json={"url": YT}).json()
    assert r2["cached"] is True and r2["status"] == "done"
    assert FakeTranscriber.calls == 1


def test_failed_download_reports_error(client):
    c, _ = client
    job_id = c.post("/api/transcripts", json={"url": "https://example.com/bad"}).json()["job_id"]
    job = c.get(f"/api/transcripts/{job_id}").json()
    assert job["status"] == "failed" and "unavailable" in job["error"]
    assert c.get(f"/api/transcripts/{job_id}/result").status_code == 409


def test_url_validation():
    for bad in ["ftp://x.com/a", "http://localhost/a", "http://127.0.0.1/a", "not a url"]:
        with pytest.raises(ValueError):
            validate_url(bad)
