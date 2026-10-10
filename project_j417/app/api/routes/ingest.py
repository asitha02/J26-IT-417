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
