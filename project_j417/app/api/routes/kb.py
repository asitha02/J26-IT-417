from fastapi import APIRouter, HTTPException
from app.db.mongo import db

router = APIRouter(prefix="/kb", tags=["kb"])


@router.get("")
def list_kb(type: str | None = None, limit: int = 50, skip: int = 0):
    query = {"type": type} if type else {}
    items = list(db.kb_items.find(query, {"_id": 0}).skip(skip).limit(limit))
    return {"count": len(items), "items": items}


@router.get("/{kb_id}")
def get_kb_item(kb_id: str):
    item = db.kb_items.find_one({"kb_id": kb_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="KB item not found")
    return item