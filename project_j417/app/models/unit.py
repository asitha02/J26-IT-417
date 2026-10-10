from pydantic import BaseModel

class KnowledgeUnit(BaseModel):
    unit_id: str
    video_id: str
    type: str
    text: str
    timestamp: str
    confidence: float | None = None
    norm_key: str