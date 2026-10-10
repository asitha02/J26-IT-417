import re
import unicodedata
from typing import Any, Mapping

from app.core.config import MIN_CONFIDENCE, MIN_UNIT_CHARS
from app.models.ingest import IngestPayload
from app.models.unit import KnowledgeUnit

FILLERS = re.compile(r"\b(?:um+|uh+|erm|you know|i mean)\b,?", re.IGNORECASE)
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = FILLERS.sub("", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    return text.strip()


def normalize_key(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_units(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def _as_mapping(item: Any) -> Mapping[str, Any]:
    if isinstance(item, Mapping):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return vars(item)


def preprocess_payload(payload: IngestPayload) -> list[KnowledgeUnit]:
    video_id = getattr(payload, "video_id", None)
    item_list = getattr(payload, "items", [])
    units: list[KnowledgeUnit] = []

    for item in item_list:
        mapping = _as_mapping(item)
        item_type = mapping.get("type")
        text = mapping.get("text", "")
        timestamp = mapping.get("timestamp", "")
        confidence = mapping.get("confidence")

        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = None

        if confidence is not None and confidence < MIN_CONFIDENCE:
            continue

        for piece in split_units(clean_text(text)):
            if item_type != "entity" and len(piece) < MIN_UNIT_CHARS:
                continue
            units.append(
                KnowledgeUnit(
                    unit_id=f"{video_id}:{len(units)}",
                    video_id=video_id,
                    type=item_type,
                    text=piece,
                    timestamp=timestamp,
                    confidence=confidence,
                    norm_key=normalize_key(piece),
                )
            )

    return units
