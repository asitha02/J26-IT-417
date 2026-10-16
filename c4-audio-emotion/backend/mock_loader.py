"""
Loads the DUMMY inputs that stand in for other components:
  - C3 audience sentiment   (mock_data/component3_sentiment.json)
  - knowledge gaps          (mock_data/knowledge_gaps.json)

All knowledge of the file formats lives in THIS file. When the real C3 output
or real knowledge-gap data is available, only these two functions change;
fusion.py keeps receiving the same dict shapes (CLAUDE.md sections 8.3 and 8.4).
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


def load_c3_sentiment(video_id: str) -> dict:
    """Dummy C3 output: overall sentiment, complaints, requested topics, timestamped comments."""
    return _pick_mock("component3_sentiment.json", video_id)


def load_knowledge_gaps(video_id: str) -> dict:
    """Dummy knowledge gaps: topics mentioned but not explained, with their time ranges."""
    return _pick_mock("knowledge_gaps.json", video_id)
