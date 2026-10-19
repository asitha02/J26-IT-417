"""
Pydantic models = the exact JSON shapes of CLAUDE.md section 8 (8.6 for the two-part design).

FastAPI uses these to:
  - reject bad requests automatically (e.g. missing youtube_url),
  - make sure every response has the agreed field names and types,
  - show the shapes in the auto-generated docs at http://localhost:8000/docs
"""
from typing import Optional

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    youtube_url: str
    force_reanalyze: bool = False  # True = ignore the saved result and analyse again


class Overall(BaseModel):
    mean_valence: float
    mean_arousal: float
    dominant_quadrant: str


class ModelInfo(BaseModel):
    embedding_model: str
    head: str
    mock: bool  # True = fake values from MockEmotionModel, not a real analysis


class Summary(BaseModel):
    """One row in a list of past results."""
    video_id: str
    title: str
    created_at: str


# ---------- Part 1: Affective Audio Analysis ----------

class AudioSegment(BaseModel):
    start_s: float
    end_s: float
    valence: float                  # background MUSIC: -1 (negative) .. +1 (positive)
    arousal: float                  # background MUSIC: -1 (calm) .. +1 (energetic)
    quadrant: str
    mixed_valence: float            # same window, unseparated audio (for comparison)
    mixed_arousal: float
    speech_db: float                # loudness of the narration
    music_db: float                 # loudness of the background music
    music_minus_speech_db: Optional[float]   # None when nobody is speaking
    clipping_pct: float
    silent: bool
    music_label: Optional[str]      # CLAP's best description of this window's music


class Separation(BaseModel):
    method: str                     # "htdemucs" or "none"
    speech_db: float
    music_db: float


class MusicLabel(BaseModel):
    label: str
    score: float                    # 0..1 (share of CLAP's matching, top 3 shown)


class AudioProblem(BaseModel):
    type: str                       # music_too_loud / clipping / silence
    severity: str
    start_s: float
    end_s: float
    description: str
    evidence: list[str]


class AudioAnalysisResponse(BaseModel):
    video_id: str
    youtube_url: str
    title: str
    analyzed_seconds: float
    segment_seconds: int
    hop_seconds: int
    model_info: ModelInfo
    separation: Separation
    segments: list[AudioSegment]
    overall: Overall                # background music
    overall_mixed: Overall          # unseparated audio
    music_description: list[MusicLabel]
    audio_problems: list[AudioProblem]
    status: str
    created_at: str                 # ISO-8601 timestamp


# ---------- Part 2: Content Enhancement Recommendations ----------

class Recommendation(BaseModel):
    id: str
    rule_id: str
    type: str
    severity: str                   # low / medium / high
    start_s: float
    end_s: float
    title: str
    evidence: list[str]
    suggestion: str
    confidence: float               # 0..1
    link: str                       # opens the video at start_s


class SectionSummary(BaseModel):
    start_s: float
    end_s: float
    topic: str
    content_type: str
    music_mood: str
    music_loudness: str
    negative_comments: int
    knowledge_gaps: list[str]
    observations: list[str]


class Validation(BaseModel):
    flagged_segments: int
    agreeing_segments: int
    agreement: Optional[float]
    random_baseline: Optional[float]
    lift: Optional[float]
    explanation: str
    mock_data: bool


class RecommendationReport(BaseModel):
    video_id: str
    youtube_url: str
    title: str
    inputs: dict
    section_summaries: list[SectionSummary]
    recommendations: list[Recommendation]
    validation: Validation
    status: str
    created_at: str
