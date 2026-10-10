from typing import Any

from pydantic import BaseModel


class IngestPayload(BaseModel):
    video_id: str
    items: list[dict[str, Any]] = []
