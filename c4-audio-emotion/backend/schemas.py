"""
Pydantic models = the exact JSON shapes of CLAUDE.md section 8.

FastAPI uses these to:
  - reject bad requests automatically (e.g. missing youtube_url),
  - make sure every response has the agreed field names and types,
  - show the shapes in the auto-generated docs at http://localhost:8000/docs
"""
from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    youtube_url: str
    force_reanalyze: bool = False  # True = ignore the saved result and analyse again


class Segment(BaseModel):
    start_s: float
    end_s: float
    valence: float   # -1 (negative) .. +1 (positive)
    arousal: float   # -1 (calm) .. +1 (energetic)
    quadrant: str    # energetic_positive / tense_negative / low_negative / calm_positive


class Overall(BaseModel):
    mean_valence: float
    mean_arousal: float
    dominant_quadrant: str


class ModelInfo(BaseModel):
    embedding_model: str
    head: str
    mock: bool  # True = fake values from MockEmotionModel, not a real analysis


class Recommendation(BaseModel):
    id: str
    rule_id: str
    type: str
    severity: str        # low / medium / high
    start_s: float
    end_s: float
    title: str
    evidence: list[str]
    suggestion: str
    confidence: float    # 0..1


class AnalysisResponse(BaseModel):
    video_id: str
    youtube_url: str
    title: str
    analyzed_seconds: float
    segment_seconds: int
    hop_seconds: int
    model_info: ModelInfo
    segments: list[Segment]
    overall: Overall
    c3_input: dict       # dummy C3 sentiment (filled in on Day 11)
    gaps_input: dict     # dummy knowledge gaps (filled in on Day 11)
    recommendations: list[Recommendation]
    status: str
    created_at: str      # ISO-8601 timestamp


class AnalysisSummary(BaseModel):
    """One row in the list of past analyses (GET /analyses)."""
    video_id: str
    title: str
    created_at: str
