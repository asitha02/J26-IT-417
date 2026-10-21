"""MongoDB access for jobs and transcripts."""

import uuid
from datetime import datetime, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def transcript_key(source_id: str, asr_model: str) -> str:
    return f"{source_id}__{asr_model}"


class Repository:
    def __init__(self, db):
        self.jobs = db["transcription_jobs"]
        self.transcripts = db["transcripts"]
        self.embeddings = db["window_embeddings"]

    async def ensure_indexes(self) -> None:
        await self.jobs.create_index([("created_at", -1)])
        await self.jobs.create_index("status")
        await self.transcripts.create_index("source_id")

    # ---- jobs ----
    async def create_job(self, url: str, **extra: Any) -> dict:
        now = _now()
        job = {
            "_id": uuid.uuid4().hex,
            "status": "queued",
            "progress": 0.0,
            "source_url": url,
            "cached": False,
            "created_at": now,
            "updated_at": now,
            **extra,
        }
        await self.jobs.insert_one(job)
        return job

    async def update_job(self, job_id: str, **fields: Any) -> None:
        fields["updated_at"] = _now()
        await self.jobs.update_one({"_id": job_id}, {"$set": fields})

    async def get_job(self, job_id: str) -> dict | None:
        return await self.jobs.find_one({"_id": job_id})

    async def list_jobs(self, limit: int = 20) -> list[dict]:
        cursor = self.jobs.find().sort("created_at", -1).limit(limit)
        return [doc async for doc in cursor]

    async def fail_unfinished(self) -> int:
        """Jobs left mid-flight by a server restart can never finish - mark them failed."""
        res = await self.jobs.update_many(
            {"status": {"$in": ["queued", "downloading", "transcribing"]}},
            {"$set": {"status": "failed", "error": "Server restarted", "updated_at": _now()}},
        )
        return res.modified_count

    # ---- transcripts ----
    async def get_transcript(self, transcript_id: str) -> dict | None:
        return await self.transcripts.find_one({"_id": transcript_id})

    async def find_cached(self, source_id: str, asr_model: str, need_words: bool) -> dict | None:
        doc = await self.get_transcript(transcript_key(source_id, asr_model))
        if doc is None:
            return None
        if need_words and not doc.get("has_words"):
            return None
        return doc

    async def list_transcripts(self, source_ids: list[str] | None = None) -> list[dict]:
        query = {"source_id": {"$in": source_ids}} if source_ids else {}
        return [doc async for doc in self.transcripts.find(query)]

    # ---- stored window embeddings (segment selection) ----
    async def get_embeddings(self, key: str) -> dict | None:
        return await self.embeddings.find_one({"_id": key})

    async def save_embeddings(self, key: str, sig: str, vectors: list[list[float]]) -> None:
        await self.embeddings.replace_one(
            {"_id": key}, {"_id": key, "sig": sig, "vectors": vectors}, upsert=True
        )

    async def save_transcript(self, doc: dict) -> str:
        tid = transcript_key(doc["source_id"], doc["asr_model"])
        doc = {**doc, "_id": tid}
        await self.transcripts.replace_one({"_id": tid}, doc, upsert=True)
        return tid
