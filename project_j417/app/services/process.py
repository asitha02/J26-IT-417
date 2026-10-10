import re
import unicodedata

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
    """Lowercase, punctuation-free key for exact-duplicate matching."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_units(text: str) -> list[str]:
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]


def preprocess_payload(payload: IngestPayload) -> list[KnowledgeUnit]:
    units: list[KnowledgeUnit] = []
    for item in payload.items:
        if item.confidence is not None and item.confidence < MIN_CONFIDENCE:
            continue
        for piece in split_units(clean_text(item.text)):
            # entities can legitimately be short ("Alan Turing")
            if item.type != "entity" and len(piece) < MIN_UNIT_CHARS:
                continue
            units.append(
                KnowledgeUnit(
                    unit_id=f"{payload.video_id}:{len(units)}",
                    video_id=payload.video_id,
                    type=item.type,
                    text=piece,
                    timestamp=item.timestamp,
                    confidence=item.confidence,
                    norm_key=normalize_key(piece),
                )
            )
    return units