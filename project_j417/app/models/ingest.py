from pydantic import BaseModel


class IngestItem(BaseModel):
    type: str
    text: str
    timestamp: str
    confidence: float | None = None


class IngestPayload(BaseModel):
    video_id: str
    items: list[IngestItem] = []
