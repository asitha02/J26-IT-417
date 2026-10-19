"""
MongoDB helpers for C4.

Two collections, one per part of the component (CLAUDE.md section 8.6):
  audio_analyses          Part 1 results (one document per video)
  recommendation_reports  Part 2 results (one document per video)
In both, video_id is unique, so analysing the same video again replaces the old document.
"""
from pymongo import MongoClient

from backend.config import AUDIO_ANALYSES_COLLECTION, MONGODB_DB, MONGODB_URI

_client = None           # created once, then reused (opening a connection is slow)
_indexed = set()         # collections that already have their unique index


def get_collection(name: str = AUDIO_ANALYSES_COLLECTION):
    """Return a collection, connecting to MongoDB on first use."""
    global _client
    if not MONGODB_URI:
        raise RuntimeError("MONGODB_URI is not set. Copy .env.example to .env and fill it in.")
    if _client is None:
        # Fail after 5 s instead of hanging if Atlas cannot be reached.
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    collection = _client[MONGODB_DB][name]
    if name not in _indexed:
        # Unique index: at most one document per video (safe to call more than once).
        collection.create_index("video_id", unique=True)
        _indexed.add(name)
    return collection


def _without_mongo_id(doc):
    """Remove Mongo's internal _id (an ObjectId, which can't be turned into JSON)."""
    if doc is not None:
        doc.pop("_id", None)
    return doc


def ping():
    """Check the database is reachable. Raises an error if not."""
    get_collection()
    _client.admin.command("ping")


def save(doc: dict, collection: str = AUDIO_ANALYSES_COLLECTION) -> None:
    """Insert the document, or replace the existing one for the same video_id."""
    get_collection(collection).replace_one({"video_id": doc["video_id"]}, doc, upsert=True)


def get(video_id: str, collection: str = AUDIO_ANALYSES_COLLECTION):
    """Return the stored document for this video, or None if there is none."""
    return _without_mongo_id(get_collection(collection).find_one({"video_id": video_id}))


def list_summaries(collection: str = AUDIO_ANALYSES_COLLECTION) -> list:
    """Return a short summary (video_id, title, created_at) of every stored document, newest first."""
    cursor = get_collection(collection).find(
        {}, {"_id": 0, "video_id": 1, "title": 1, "created_at": 1}
    ).sort("created_at", -1)
    return list(cursor)


def delete(video_id: str, collection: str = AUDIO_ANALYSES_COLLECTION) -> None:
    """Delete the document for this video (used by the test script to clean up)."""
    get_collection(collection).delete_one({"video_id": video_id})
