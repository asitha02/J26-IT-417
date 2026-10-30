"""
Loads the DUMMY inputs that stand in for the other components (Part 2 inputs):
  - C1 transcript sections  (mock_data/component1_transcript.json)
  - C2 knowledge gaps       (mock_data/knowledge_gaps.json)
  - C3 audience sentiment   (mock_data/component3_sentiment.json)

All knowledge of the file formats lives in THIS file. When the real C1, C2 or C3
outputs are available, only these functions change; fusion.py keeps receiving the
same dict shapes (CLAUDE.md sections 8.3, 8.4 and 8.6).
"""
import json

from backend.config import MOCK_DATA_DIR


def _pick_mock(filename: str, video_id: str) -> dict:
    """Return the mock entry for this video, or the 'default' entry if the video isn't listed."""
    with open(MOCK_DATA_DIR / filename, encoding="utf-8") as f:
        mocks = json.load(f)["mocks"]
    by_id = {m["video_id"]: m for m in mocks}
    entry = dict(by_id.get(video_id, by_id["default"]))  # copy, so the file data isn't changed
    entry["video_id"] = video_id
    entry["mock"] = True        # always marked, so nobody mistakes it for real analysis
    return entry


def load_c1_transcript(video_id: str) -> dict:
    """Dummy C1 output: transcript sections with topic and content type (hook / explanation / ...)."""
    return _pick_mock("component1_transcript.json", video_id)


def load_c3_sentiment(video_id: str) -> dict:
    """Dummy C3 output: overall sentiment, complaints, requested topics, timestamped comments."""
    return _pick_mock("component3_sentiment.json", video_id)


def load_knowledge_gaps(video_id: str) -> dict:
    """Dummy C2 output: knowledge gaps (topics mentioned but not explained), with their time ranges."""
    return _pick_mock("knowledge_gaps.json", video_id)
