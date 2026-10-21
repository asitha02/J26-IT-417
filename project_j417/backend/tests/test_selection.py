"""Segment-selection ranking: windowing, BM25 ranking, overlap/diversity rules, and the API."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import AsrConfig
from app.main import create_app
from app.selection.ranker import Embedder, build_windows, rank_windows


def _segments(lines, step=10.0):
    return [
        {"id": i, "start": i * step, "end": (i + 1) * step, "text": t, "confidence": 0.9}
        for i, t in enumerate(lines)
    ]


COOKING = _segments(
    [
        "Welcome back to the channel everyone.",
        "Today we talk about sourdough starter and how to feed it.",
        "Flour and water ratio matters for the starter fermentation.",
        "Please like and subscribe before we continue.",
        "Next we shape the loaf and bake it in a dutch oven.",
        "Thanks for watching, see you next time.",
    ]
)
TECH = _segments(
    [
        "In this lecture we cover neural network training.",
        "Gradient descent updates the weights using the loss gradient.",
        "Overfitting happens when the model memorises the training data.",
        "That is all for today.",
    ]
)


def test_windows_cover_transcript_and_move_forward():
    wins = build_windows("v", COOKING, window_sec=30)
    assert wins[0].start == 0 and wins[-1].end == 60
    assert all(b.start > a.start for a, b in zip(wins, wins[1:]))
    assert all(w.end - w.start >= 20 for w in wins[:-1])


def test_bm25_ranks_relevant_window_first_and_dedups_overlap():
    wins = build_windows("cook", COOKING, 30) + build_windows("tech", TECH, 30)
    clips, method = rank_windows(wins, "sourdough starter feeding", None, top_k=5)
    assert method == "bm25"
    assert clips[0].window.source_id == "cook"
    assert "sourdough" in clips[0].window.text
    same = [c.window for c in clips if c.window.source_id == "cook"]
    for i, a in enumerate(same):  # no two chosen clips from a video overlap heavily
        for b in same[i + 1 :]:
            assert min(a.end, b.end) - max(a.start, b.start) < 0.3 * min(a.end - a.start, b.end - b.start)
    assert all(0 <= c.score <= 1 for c in clips)


def test_per_video_cap_and_no_match():
    wins = build_windows("cook", COOKING, 15)
    clips, _ = rank_windows(wins, "starter flour water", None, top_k=10, per_video_max=1)
    assert len(clips) == 1
    none, _ = rank_windows(wins, "quantum chromodynamics", None)
    assert none == []


def test_clean_text_removes_redundancy():
    from app.selection.clean import clean_segments, clean_text

    assert clean_text("So um, the the model uh trains, you know, on on data.") == "So the model trains, on data."
    assert clean_text("I think I think this works. Please like and subscribe!") == "I think this works."
    assert clean_text("Do you know the answer?") == "Do you know the answer?"  # meaningful use kept
    segs = [{"id": 0, "start": 0, "end": 2, "text": "Um, uh."}, {"id": 1, "start": 2, "end": 5, "text": "Real content here today."}]
    assert [s["id"] for s in clean_segments(segs)] == [1]


def test_duplicate_content_and_thin_windows_dropped():
    line = "The telescope collects faint light from distant galaxies across the universe."
    a = build_windows("a", _segments([line] * 3), 30)
    b = build_windows("b", _segments([line] * 3), 30)  # same content re-uploaded
    assert len(a) == 1  # identical overlapping windows collapse to one
    clips, _ = rank_windows(a + b, "telescope galaxies light", None, top_k=5, per_video_max=None)
    assert len(clips) == 1
    assert build_windows("c", _segments(["Okay.", "Yes."]), 30) == []  # too little substance


class FakeRepo:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.docs = [
            {"_id": "cook__m", "source_id": "cook", "source_url": "https://www.youtube.com/watch?v=cook",
             "title": "Sourdough 101", "language": "en", "created_at": now, "segments": COOKING},
            {"_id": "tech__m", "source_id": "tech", "source_url": "https://example.com/lecture",
             "title": "ML lecture", "language": "en", "created_at": now, "segments": TECH},
        ]

    async def list_transcripts(self, source_ids=None):
        return [d for d in self.docs if not source_ids or d["source_id"] in source_ids]


class FakeTranscriber:
    cfg = AsrConfig("fake", "cpu", "int8", 8, 5)


@pytest.fixture
def client():
    app = create_app()
    app.state.repo, app.state.transcriber, app.state.embedder = FakeRepo(), FakeTranscriber(), Embedder(None)
    with TestClient(app) as c:
        yield c


def test_rank_endpoint(client):
    r = client.post("/api/segments/rank", json={"query": "gradient descent weights", "top_k": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "bm25" and body["videos_searched"] == 2
    top = body["clips"][0]
    assert top["source_id"] == "tech" and top["rank"] == 1
    assert top["watch_url"] == "https://example.com/lecture#t=0"

    r = client.post("/api/segments/rank", json={"query": "sourdough", "source_ids": ["cook"], "audience": "beginners"})
    top = r.json()["clips"][0]
    assert top["watch_url"].startswith("https://www.youtube.com/watch?v=cook&t=")


def test_library_and_validation(client):
    assert {i["source_id"] for i in client.get("/api/segments/library").json()} == {"cook", "tech"}
    assert client.post("/api/segments/rank", json={"query": "x"}).status_code == 422
    assert client.post("/api/segments/rank", json={"query": "anything", "source_ids": ["nope"]}).status_code == 404
