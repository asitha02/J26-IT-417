from fastapi import APIRouter
from pydantic import BaseModel

from app.db.mongo import db
from app.models.ingest import IngestPayload
from app.services.dedupe import group_units
from app.services.embedding import embed_texts
from app.services.merge import merge_groups
from app.services.preprocess import preprocess_payload

router = APIRouter(prefix="/fusion", tags=["fusion"])


class FusionRequest(BaseModel):
    video_ids: list[str] | None = None   # None = all ingested videos


@router.post("/run")
def run_fusion(req: FusionRequest):
    query = {"video_id": {"$in": req.video_ids}} if req.video_ids else {}
    units = []
    for doc in db.raw_extractions.find(query):
        doc.pop("_id", None)
        units.extend(preprocess_payload(IngestPayload(**doc)))

    if not units:
        return {"units_in": 0, "kb_items_out": 0, "reduction_pct": 0.0}

    embeddings = embed_texts([u.text for u in units])
    groups = group_units(units, embeddings)
    items = merge_groups(units, groups)

    db.kb_items.delete_many({})
    db.kb_items.insert_many([i.model_dump() for i in items])

    return {
        "units_in": len(units),
        "kb_items_out": len(items),
        "reduction_pct": round(100 * (1 - len(items) / len(units)), 1),
    }