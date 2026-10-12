from fastapi import APIRouter

from app.db.mongo import db
from app.models.ingest import IngestPayload

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("")
def ingest(payload: IngestPayload):
    if db is None:
        return {"video_id": payload.video_id, "items": len(payload.items)}

    db.raw_extractions.replace_one(
        {"video_id": payload.video_id},
        payload.model_dump(),
        upsert=True,
    )
    return {"video_id": payload.video_id, "items": len(payload.items)}

import json
from typing import Any

from fastapi import APIRouter, Body, File, HTTPException, UploadFile

from app.db.mongo import db
from app.models.ingest import IngestPayload
from app.services.adapter import to_payloads

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _store(payloads: list[IngestPayload]) -> dict:
    for p in payloads:
        db.raw_extractions.replace_one({"video_id": p.video_id}, p.model_dump(), upsert=True)
    return {"videos": [p.video_id for p in payloads],
            "items": sum(len(p.items) for p in payloads)}


@router.post("")
def ingest(payload: IngestPayload):
    return _store([payload])


@router.post("/raw")
def ingest_raw(raw: Any = Body(...)):
    try:
        return _store(to_payloads(raw))
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e))


@router.post("/file")
async def ingest_file(file: UploadFile = File(...)):
    try:
        raw = json.loads((await file.read()).decode("utf-8"))
        return _store(to_payloads(raw))
    except json.JSONDecodeError:
        raise HTTPException(422, "File is not valid JSON")
    except (ValueError, KeyError) as e:
        raise HTTPException(422, str(e))