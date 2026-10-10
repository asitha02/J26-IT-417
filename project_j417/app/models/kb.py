from pydantic import BaseModel

class Source(BaseModel):
    video_id: str
    timestamp: str
    unit_id: str

class KBItem(BaseModel):
    kb_id: str
    type: str
    text: str                  # canonical wording
    variants: list[str] = []   # other phrasings, kept so no information is lost
    sources: list[Source]      # every video and timestamp it came from
    merged_from: int