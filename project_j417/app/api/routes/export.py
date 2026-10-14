from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.db.mongo import require_db

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/kb.txt", response_class=PlainTextResponse)
def kb_as_text():
    db = require_db()
    lines = []
    for it in db.kb_items.find({}, {"_id": 0}):
        srcs = ", ".join(f"{s['video_id']}@{s['timestamp']}" for s in it["sources"])
        lines.append(f"[{it['kb_id']}] ({it['type']}) {it['text']} | sources: {srcs}")
    if not lines:
        raise HTTPException(404, "KB is empty. Run /fusion/run first.")
    return "\n".join(lines)


@router.get("/generated.txt", response_class=PlainTextResponse)
def latest_generated(output_type: str = "summary", language: str = "en"):
    db = require_db()
    doc = db.generated_content.find_one(
        {"output_type": output_type, "language": language}, sort=[("_id", -1)]
    )
    if not doc:
        raise HTTPException(404, "Nothing generated yet. Call POST /generate first.")
    return doc["content"]