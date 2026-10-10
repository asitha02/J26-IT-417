from fastapi import APIRouter

from app.db.mongo import ping_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    ping_db()
    return {"status": "ok"}
