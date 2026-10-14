from pymongo import MongoClient
from fastapi import HTTPException

from app.core.config import MONGODB_DB, MONGODB_URI

_DB_UNAVAILABLE = (
    "MongoDB is unavailable. Check MONGODB_URI in the backend .env file "
    "and confirm that the database is reachable."
)


def _connect_database():
    if not MONGODB_URI:
        return None, None

    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000, connectTimeoutMS=2000)
        mongo_client.admin.command("ping")
        return mongo_client, mongo_client[MONGODB_DB]
    except Exception:
        return None, None


client, db = _connect_database()


def ping_db():
    if client is None:
        raise RuntimeError(_DB_UNAVAILABLE)
    try:
        return client.admin.command("ping")
    except Exception as exc:
        raise RuntimeError(_DB_UNAVAILABLE) from exc


def require_db():
    if db is None:
        raise HTTPException(status_code=503, detail=_DB_UNAVAILABLE)
    return db
