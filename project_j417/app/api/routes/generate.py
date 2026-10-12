from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.mongo import db
from app.services.consistency import check_consistency
from app.services.generator import generate
from app.services.translator import translate_with_pairs

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    output_type: Literal["summary", "notes", "quiz"]
    language: Literal["en", "si"] = "en"
    kb_ids: list[str] | None = None


@router.post("")
def generate_content(req: GenerateRequest):
    query = {"kb_id": {"$in": req.kb_ids}} if req.kb_ids else {}
    items = list(db.kb_items.find(query, {"_id": 0, "embedding": 0}).limit(200))
    if not items:
        raise HTTPException(404, "No KB items found. Run /fusion/run first.")

    english = generate(req.output_type, items)
    doc = {
        "output_type": req.output_type,
        "language": req.language,
        "content_en": english,
        "content": english,
        "kb_ids": [i["kb_id"] for i in items],
    }
    if req.language == "si":
        sinhala, pairs = translate_with_pairs(english, target="si")
        doc["content"] = sinhala
        doc["consistency"] = check_consistency(pairs)

    db.generated_content.insert_one(dict(doc))
    return doc

    from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.mongo import db
from app.services.consistency import check_consistency
from app.services.generator import generate
from app.services.translator import translate_with_pairs

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateRequest(BaseModel):
    output_type: Literal["summary", "notes", "quiz"]
    language: Literal["en", "si"] = "en"
    kb_ids: list[str] | None = None


@router.post("")
def generate_content(req: GenerateRequest):
    query = {"kb_id": {"$in": req.kb_ids}} if req.kb_ids else {}
    items = list(db.kb_items.find(query, {"_id": 0}).limit(200))
    if not items:
        raise HTTPException(404, "No KB items found. Run /fusion/run first.")

    english = generate(req.output_type, items)
    doc = {
        "output_type": req.output_type,
        "language": req.language,
        "content_en": english,
        "content": english,
        "kb_ids": [i["kb_id"] for i in items],
    }
    if req.language == "si":
        sinhala, pairs = translate_with_pairs(english, target="si")
        doc["content"] = sinhala
        doc["consistency"] = check_consistency(pairs)

    db.generated_content.insert_one(dict(doc))
    return doc