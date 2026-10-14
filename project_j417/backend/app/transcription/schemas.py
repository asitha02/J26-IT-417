"""API models. `TranscriptOut` is the JSON contract handed to the knowledge-fusion component."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

JobStatusLiteral = Literal["queued", "downloading", "transcribing", "done", "failed"]


class TranscriptCreate(BaseModel):
    url: str = Field(min_length=8, max_length=2048, description="YouTube / podcast / audio URL")
    language: str | None = Field(
        default=None, max_length=8, description="ISO code (e.g. 'en'). Omit to auto-detect."
    )
    word_timestamps: bool = Field(
        default=False, description="Add per-word timestamps (slightly slower)."
    )


class JobOut(BaseModel):
    job_id: str
    status: JobStatusLiteral
    progress: float = 0.0
    source_url: str
    source_id: str | None = None
    title: str | None = None
    duration_sec: float | None = None
    transcript_id: str | None = None
    cached: bool = False
    processing_time_sec: float | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class Word(BaseModel):
    start: float
    end: float
    word: str
    probability: float | None = None


class Segment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    confidence: float | None = None
    words: list[Word] | None = None


class TranscriptOut(BaseModel):
    schema_version: str = "1.0"
    source_id: str
    source_url: str
    title: str | None = None
    uploader: str | None = None
    duration_sec: float | None = None
    language: str
    language_probability: float | None = None
    asr_model: str
    device: str
    created_at: datetime
    processing_time_sec: float
    full_text: str
    segments: list[Segment]
