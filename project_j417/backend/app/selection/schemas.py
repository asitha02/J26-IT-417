from typing import Literal

from pydantic import BaseModel, Field


class RankRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500, description="Topic to look for")
    audience: str | None = Field(None, max_length=200, description="e.g. 'beginners', 'clinicians'")
    source_ids: list[str] | None = Field(None, description="Restrict to these videos (default: all)")
    top_k: int = Field(10, ge=1, le=50)
    window_sec: float = Field(30, ge=10, le=120)
    per_video_max: int | None = Field(3, ge=1, le=50, description="Max clips from a single video")


class Clip(BaseModel):
    rank: int
    source_id: str
    title: str | None = None
    source_url: str
    watch_url: str
    start: float
    end: float
    score: float = Field(description="Relevance, 0-1 (relative to this collection)")
    lexical_score: float
    semantic_score: float | None = None
    text: str


class RankResponse(BaseModel):
    query: str
    audience: str | None = None
    method: Literal["hybrid", "bm25"]
    embedding_model: str | None = None
    videos_searched: int
    windows_searched: int
    elapsed_sec: float
    clips: list[Clip]


class LibraryItem(BaseModel):
    source_id: str
    title: str | None = None
    source_url: str
    duration_sec: float | None = None
    language: str | None = None
    segments: int
