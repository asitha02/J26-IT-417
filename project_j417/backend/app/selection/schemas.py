from typing import Literal

from pydantic import BaseModel, Field


class RankRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500, description="Topic to look for")
    audience: str | None = Field(None, max_length=200, description="e.g. 'beginners', 'clinicians'")
    source_ids: list[str] | None = Field(None, description="Restrict to these videos (default: all)")
    top_k: int = Field(10, ge=1, le=50)
    window_sec: float = Field(30, ge=10, le=120)
    per_video_max: int | None = Field(3, ge=1, le=50, description="Max clips from a single video")
    ranker: Literal["auto", "fixed"] = Field(
        "auto", description="auto = use the trained ranker if one exists; fixed = 35/65 keyword/semantic blend"
    )


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
    features: dict[str, float] = Field(default_factory=dict, description="Ranking signals for this clip")


class RankResponse(BaseModel):
    query: str
    audience: str | None = None
    method: Literal["learned", "hybrid", "bm25"]
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


class LabelIn(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    audience: str | None = Field(None, max_length=200)
    source_id: str
    start: float
    end: float
    label: Literal[0, 1] | None = Field(description="1 relevant, 0 not relevant, null removes the label")
    features: dict[str, float]


class LabelStats(BaseModel):
    labels: int
    positives: int
    negatives: int
    queries: int
    ready_to_train: bool
    needs: str | None = None


class ModelInfo(BaseModel):
    trained: bool
    trained_at: str | None = None
    report: dict | None = None
