import os
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

load_dotenv()

client = MongoClient(os.environ["MONGODB_URI"])
db = client[os.getenv("MONGODB_DB", "project_j417")]
items = db["items"]

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
    doc["id"] = str(doc.pop("_id"))
    return doc


def to_oid(item_id: str) -> ObjectId:
    try:
        return ObjectId(item_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid id")


@app.get("/health")
def health():
    client.admin.command("ping")
    return {"status": "ok"}


@app.post("/items", status_code=201)
def create_item(item: ItemIn):
    result = items.insert_one(item.model_dump())
    return serialize(items.find_one({"_id": result.inserted_id}))


@app.get("/items")
def list_items():
    return [serialize(d) for d in items.find()]


@app.get("/items/{item_id}")
def get_item(item_id: str):
    doc = items.find_one({"_id": to_oid(item_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Item not found")
    return serialize(doc)


@app.put("/items/{item_id}")
def update_item(item_id: str, item: ItemIn):
    result = items.update_one({"_id": to_oid(item_id)}, {"$set": item.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return serialize(items.find_one({"_id": to_oid(item_id)}))


@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str):
    result = items.delete_one({"_id": to_oid(item_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
