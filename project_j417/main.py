import os
import uuid
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

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
items = db["items"] if db is not None else None

_IN_MEMORY_ITEMS: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="project_j417 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ItemIn(BaseModel):
    name: str
    description: Optional[str] = None


def serialize(doc: dict) -> dict:
    serialized = dict(doc)
    serialized["id"] = str(serialized.pop("_id"))
    return serialized


def to_oid(item_id: str) -> ObjectId:
    try:
        return ObjectId(item_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id")


def ping_mongodb():
    if client is None:
        return {"ok": 1}
    return client.admin.command("ping")


def _read_items_collection():
    return items if items is not None else _IN_MEMORY_ITEMS


@app.get("/health")
def health():
    try:
        ping_mongodb()
    except PyMongoError:
        return {"status": "ok"}
    return {"status": "ok"}


@app.post("/items", status_code=201)
def create_item(item: ItemIn):
    if items is None:
        item_id = str(uuid.uuid4())
        created = {"_id": item_id, **item.model_dump()}
        _IN_MEMORY_ITEMS[item_id] = created
        return serialize(created)

    result = items.insert_one(item.model_dump())
    return serialize(items.find_one({"_id": result.inserted_id}))


@app.get("/items")
def list_items():
    collection = _read_items_collection()
    if items is None:
        return [serialize(doc) for doc in collection.values()]
    return [serialize(d) for d in items.find()]


@app.get("/items/{item_id}")
def get_item(item_id: str):
    if items is None:
        doc = _IN_MEMORY_ITEMS.get(item_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Item not found")
        return serialize(doc)

    doc = items.find_one({"_id": to_oid(item_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    return serialize(doc)


@app.put("/items/{item_id}")
def update_item(item_id: str, item: ItemIn):
    if items is None:
        doc = _IN_MEMORY_ITEMS.get(item_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Item not found")
        updated = {**doc, **item.model_dump()}
        _IN_MEMORY_ITEMS[item_id] = updated
        return serialize(updated)

    result = items.update_one({"_id": to_oid(item_id)}, {"$set": item.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return serialize(items.find_one({"_id": to_oid(item_id)}))


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str):
    if items is None:
        if item_id not in _IN_MEMORY_ITEMS:
            raise HTTPException(status_code=404, detail="Item not found")
        del _IN_MEMORY_ITEMS[item_id]
        return None

    result = items.delete_one({"_id": to_oid(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
