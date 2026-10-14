from fastapi import APIRouter, HTTPException

from app.db.mongo import ping_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    try:
        ping_db()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "ok"}
