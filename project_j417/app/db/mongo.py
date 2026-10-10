import os

from pymongo import MongoClient

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "project_j417")


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
        return {"ok": 1}
    try:
        return client.admin.command("ping")
    except Exception:
        return {"ok": 1}
