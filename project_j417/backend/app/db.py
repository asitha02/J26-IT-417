"""MongoDB connection.

If your base project already has a connection module, delete this file and
make `main.py` / `repository.py` use your existing database handle instead.
Only `Repository(db)` needs an `AsyncDatabase`-like object.
"""

from pymongo import AsyncMongoClient

from app.config import Settings

_client: AsyncMongoClient | None = None


async def connect(settings: Settings):
    global _client
    _client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    return _client[settings.mongodb_db]


async def close() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
