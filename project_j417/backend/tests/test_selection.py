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


def _synthetic_samples(n_queries=8, per_query=14, seed=0):
    """Labels driven mostly by `semantic` (+ a little `coverage`); other features are noise."""
    import numpy as np

    from app.selection.learned import FEATURES

    rng = np.random.default_rng(seed)
    samples = []
    for q in range(n_queries):
        for _ in range(per_query):
            f = {name: float(rng.random()) for name in FEATURES}
            label = int(f["semantic"] + 0.3 * f["coverage"] + rng.normal(0, 0.1) > 0.85)
            samples.append({"features": f, "label": label, "group": f"q{q}"})
    return samples


def test_learned_ranker_finds_the_signal_and_beats_noise_baseline(tmp_path):
    from app.selection.learned import LearnedRanker, train

    model = train(_synthetic_samples())
    rep = model.report
    assert rep["weights"]["semantic"] == max(rep["weights"].values())  # it learned what drives relevance
    assert rep["metrics"]["learned"]["ndcg@10"] >= rep["metrics"]["bm25"]["ndcg@10"]  # bm25 col is noise here
    path = tmp_path / "m.json"
    model.save(path)
    assert LearnedRanker.load(path).weights == model.weights


def test_training_refuses_too_little_data():
    from app.selection.learned import TrainingError, train

    with pytest.raises(TrainingError, match="Need at least"):
        train(_synthetic_samples(n_queries=1, per_query=6))


def test_learned_model_is_used_by_rank_windows():
    from app.selection.learned import FEATURES, LearnedRanker

    class Stub(Embedder):
        def __init__(self):
            super().__init__("stub")

        def load(self):
            return True

        def embed_docs(self, texts):
            return [[1.0, 0.0] for _ in texts]

        def embed_query(self, text):
            return [1.0, 0.0]

    model = LearnedRanker(FEATURES, [0.0] * len(FEATURES), [1.0] * len(FEATURES),
                          [0.0] * len(FEATURES), 0.0)
    wins = build_windows("cook", COOKING, 30)
    clips, method = rank_windows(wins, "sourdough starter", Stub(), model=model)
    assert method == "learned" and clips and set(clips[0].features) == set(FEATURES)


class FakeRepo:
    def __init__(self):
        self.labels = {}
        now = datetime.now(timezone.utc)
        self.docs = [
            {"_id": "cook__m", "source_id": "cook", "source_url": "https://www.youtube.com/watch?v=cook",
             "title": "Sourdough 101", "language": "en", "created_at": now, "segments": COOKING},
            {"_id": "tech__m", "source_id": "tech", "source_url": "https://example.com/lecture",
             "title": "ML lecture", "language": "en", "created_at": now, "segments": TECH},
        ]

    async def list_transcripts(self, source_ids=None):
        return [d for d in self.docs if not source_ids or d["source_id"] in source_ids]

    async def upsert_label(self, doc):
        self.labels[doc["_id"]] = doc

    async def delete_label(self, label_id):
        self.labels.pop(label_id, None)

    async def list_labels(self):
        return list(self.labels.values())


class FakeTranscriber:
    cfg = AsrConfig("fake", "cpu", "int8", 8, 5)


@pytest.fixture
def client(tmp_path):
    from app.config import Settings, get_settings

    app = create_app()
    app.state.repo, app.state.transcriber, app.state.embedder = FakeRepo(), FakeTranscriber(), Embedder(None)
    settings = Settings(data_dir=tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
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


def test_label_train_and_model_endpoints(client):
    from app.selection.learned import FEATURES

    assert client.get("/api/segments/model").json() == {"trained": False, "trained_at": None, "report": None}
    stats = client.get("/api/segments/labels/stats").json()
    assert stats["labels"] == 0 and stats["ready_to_train"] is False
    assert client.post("/api/segments/train").status_code == 422  # not enough labels yet

    for s in _synthetic_samples():
        r = client.put("/api/segments/labels", json={
            "query": f"topic {s['group']}", "source_id": "cook", "start": s["features"]["lexical"] * 1000,
            "end": 5, "label": s["label"], "features": s["features"]})
        assert r.status_code == 204
    stats = client.get("/api/segments/labels/stats").json()
    assert stats["ready_to_train"] is True and stats["queries"] == 8

    # re-labelling the same clip replaces it; null removes it
    one = client.get("/api/segments/labels").json()[0]
    body = {"query": one["query"], "source_id": one["source_id"], "start": one["start"], "end": 5,
            "label": None, "features": one["features"]}
    client.put("/api/segments/labels", json=body)
    assert client.get("/api/segments/labels/stats").json()["labels"] == stats["labels"] - 1

    trained = client.post("/api/segments/train").json()
    assert trained["trained"] and set(trained["report"]["weights"]) == set(FEATURES)
    assert client.get("/api/segments/model").json()["trained"] is True
