"""
MongoDB helpers for C4.

One document per analysed video, stored in the "analyses" collection.
The video_id is unique, so analysing the same video again replaces the old document.
"""
from pymongo import MongoClient

from backend.config import ANALYSES_COLLECTION, MONGODB_DB, MONGODB_URI

_client = None  # created once, then reused (opening a connection is slow)


def get_collection():
    """Return the 'analyses' collection, connecting to MongoDB on first use."""
    global _client
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set. Copy .env.example to .env and fill it in.")
    if _client is None:
        # Fail after 5 s instead of hanging if Atlas cannot be reached.
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        collection = _client[MONGODB_DB][ANALYSES_COLLECTION]
        # Unique index: at most one analysis per video (safe to call more than once).
        collection.create_index("video_id", unique=True)
    return _client[MONGODB_DB][ANALYSES_COLLECTION]


def _without_mongo_id(doc):
    """Remove Mongo's internal _id (an ObjectId, which can't be turned into JSON)."""
    if doc is not None:
        doc.pop("_id", None)
    return doc


def ping():
    """Check the database is reachable. Raises an error if not."""
    get_collection()
    _client.admin.command("ping")


def save_analysis(analysis: dict) -> None:
    """Insert the analysis, or replace the existing one for the same video_id."""
    get_collection().replace_one({"video_id": analysis["video_id"]}, analysis, upsert=True)


def get_analysis(video_id: str):
    """Return the stored analysis for this video, or None if it was never analysed."""
    return _without_mongo_id(get_collection().find_one({"video_id": video_id}))


def list_analyses() -> list:
    """Return a short summary of every past analysis, newest first."""
    cursor = get_collection().find(
        {}, {"_id": 0, "video_id": 1, "title": 1, "created_at": 1}
    ).sort("created_at", -1)
    return list(cursor)


def delete_analysis(video_id: str) -> None:
    """Delete the analysis for this video (used by the test script to clean up)."""
    get_collection().delete_one({"video_id": video_id})
