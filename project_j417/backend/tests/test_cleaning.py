"""The cleaning step: three small trained models (sentences, error words, duplicates), the rules they are
compared with, the cleaned JSON, and the API."""

import random
from datetime import datetime, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.cleaning import cleaner as cleaner_store
from app.cleaning import data, duplicate_model, rules, sentence_model, training, word_model
from app.cleaning.cleaner import Cleaner
from app.cleaning.ml import words_of
from app.cleaning.pipeline import clean_documents
from app.config import AsrConfig, Settings, get_settings
from app.main import create_app

GLITCH = "The telescope collects faint light from distant galaxies across the universe."


def _doc(source_id, texts, confs=None, created=0):
    segs = [{"id": i, "start": i * 10.0, "end": i * 10.0 + 9.0, "text": t, "confidence": (confs or {}).get(i, 0.9)}
            for i, t in enumerate(texts)]
    return {"_id": f"{source_id}__m", "source_id": source_id, "source_url": f"https://example.com/{source_id}",
            "title": source_id.title(), "created_at": datetime(2026, 1, 1 + created, tzinfo=timezone.utc),
            "asr_model": "m", "language": "en", "segments": segs}


def _content_docs(n_docs=3, n=60):
    """Ordinary educational sentences (not boilerplate), assembled from word lists so there are plenty of distinct ones."""
    rng = random.Random(7)
    subjects = ["The telescope", "A distant galaxy", "The space probe", "Our solar system", "The comet", "Light from that star",
                "The expanding universe", "A massive black hole", "The orbiting satellite", "Dust around the young star"]
    verbs = ["collects", "crosses", "reaches", "orbits", "reveals", "measures", "bends", "heats", "slows", "records"]
    objects = ["the faint radiation", "a cloud of cold gas", "the nearest planet", "an ancient burst of energy",
               "the outer edge of the disk", "twelve separate signals", "the dense stellar core", "a narrow band of light"]
    endings = ["after many thousands of years.", "far beyond the visible edge.", "every few hours.", "almost without warning.",
               "while the temperature falls.", "as the pressure slowly builds."]
    seen, out = set(), []
    while len(out) < n_docs * n:
        s = f"{rng.choice(subjects)} {rng.choice(verbs)} {rng.choice(objects)} {rng.choice(endings)}"
        if s not in seen:
            seen.add(s)
            out.append(s)
    return [_doc(f"v{d}", out[d * n : (d + 1) * n], created=d) for d in range(n_docs)]


@pytest.fixture
def small_training(monkeypatch):
    """Less data and fewer rounds, so the tests run in seconds (the real app uses the full settings)."""
    monkeypatch.setattr(sentence_model, "MAX_REAL_SENTENCES", 120)
    monkeypatch.setattr(word_model, "VARIANTS_TRAIN", 3)
    monkeypatch.setattr(word_model, "VARIANTS_TEST", 1)
    monkeypatch.setattr(word_model, "THRESHOLDS", [0.5, 0.9])
    fit = word_model.fit_logistic_sparse
    monkeypatch.setattr(word_model, "fit_logistic_sparse", lambda *a, **k: fit(*a, **{**k, "iters": 50}))


# ------------------------------------------------------------------ the rules (fallback and baseline)
def test_rules_remove_fillers_repeats_and_boilerplate():
    assert rules.clean_words("So um, the the model uh trains, you know, on on data.") == "So the model trains, on data."
    assert rules.clean_words("Do you know the answer?") == "Do you know the answer?"  # meaningful use is kept
    assert rules.is_boilerplate("Please like and subscribe to the channel.")
    assert not rules.is_boilerplate("Watch how the planets move.")
    assert rules.is_duplicate(words_of(GLITCH), words_of(GLITCH + " Today."))


# ------------------------------------------------------------------ model 2: error words
def test_word_model_learns_to_remove_fillers_and_stutters(small_training):
    base = data.base_sentences(data.real_sentences(_content_docs()))
    model, report = word_model.train(base)
    assert report["model"]["restored_exactly"] > 0.8 and report["model"]["false_edit_rate"] <= 0.05
    out = words_of(model.apply("So um, the telescope collects faint light, you know, every few hours."))
    assert "um" not in out and "know" not in out                                   # the error words are gone
    assert out[-8:] == words_of("the telescope collects faint light every few hours")  # every content word is kept
    assert "the the" not in model.apply("The comet reaches the the nearest planet far beyond the visible edge.")
    clean = "The comet reaches the nearest planet far beyond the visible edge."
    assert model.apply(clean) == clean  # nothing to remove: left exactly as it was
    again = word_model.WordModel.from_json(model.to_json())
    assert again.apply("Uh the comet reaches the nearest planet every few hours.") == model.apply("Uh the comet reaches the nearest planet every few hours.")


# ------------------------------------------------------------------ model 3: duplicates
def test_duplicate_model_separates_copies_from_different_sentences(small_training):
    base = data.base_sentences(data.real_sentences(_content_docs()))
    model, report = duplicate_model.train(base)
    assert report["model"]["f1"] > 0.85 and report["model"]["wrongly_flagged"] <= 0.1
    a = words_of("The telescope collects faint light from distant galaxies across the universe every few hours.")
    near = words_of("The telescope collects faint light from distant galaxies across the universe every hours.")
    other = words_of("A massive black hole bends the dense stellar core almost without warning.")
    assert model.is_duplicate(a, near) and not model.is_duplicate(a, other)
    again = duplicate_model.DuplicateModel.from_json(model.to_json())
    assert again.is_duplicate(a, near) is model.is_duplicate(a, near)


# ------------------------------------------------------------------ model 1: redundant sentences
def test_sentence_model_learns_boilerplate_beyond_its_examples(small_training):
    model, report = sentence_model.train(data.real_sentences(_content_docs()))
    assert report["examples"]["redundant"] == sum(len(v) for v in data.FAMILIES.values()) and len(report["never_seen_kind"]["per_kind"]) == 6
    assert model.is_redundant("Please hit that subscribe button before you leave.")  # new wording of a known idea
    assert not model.is_redundant("Light from the nearest star takes more than four years to reach us.")


def test_models_need_enough_real_text():
    with pytest.raises(training.TrainingError, match="Not enough"):
        training.train_all(_content_docs(n_docs=1, n=10))


# ------------------------------------------------------------------ the cleaned JSON
def test_cleaning_keeps_timestamps_and_ids_and_reports_what_was_removed():
    out = clean_documents([_doc("a", [
        "Um, uh.",
        "Please like and subscribe to the channel.",
        "So um, the the telescope collects faint light today.",
    ])])
    seg = out["videos"][0]["segments"]
    assert [s["id"] for s in seg] == [2] and seg[0]["start"] == 20.0 and seg[0]["end"] == 29.0
    assert seg[0]["text"] == "So the telescope collects faint light today." and "original_text" in seg[0]
    q = out["videos"][0]["quality"]
    assert q["segments_raw"] == 3 and q["segments_kept"] == 1 and q["removed"]["too_short"] == 2
    assert q["redundant_sentences_removed"] == 1 and q["error_words_removed"] > 0 and q["words_removed_pct"] > 0
    assert out["cleaning"]["trained_models_in_use"] == {"sentences": False, "words": False, "duplicates": False}


def test_duplicates_in_a_video_and_across_videos_are_removed_but_far_apart_ones_kept():
    near = clean_documents([_doc("a", [GLITCH, GLITCH, "Different content about planets orbiting around stars nearby."])])["videos"][0]
    assert [s["id"] for s in near["segments"]] == [0, 2] and near["quality"]["removed"]["duplicate_in_video"] == 1
    far_texts = [GLITCH] + [f"Unique sentence number {i} about topic {i} and subject {i}." for i in range(1, 15)] + [GLITCH]
    assert clean_documents([_doc("a", far_texts)])["videos"][0]["quality"]["removed"]["duplicate_in_video"] == 0
    two = clean_documents([_doc("b", [GLITCH], created=1), _doc("a", [GLITCH], created=0)])
    kept = {v["source_id"]: v["quality"]["segments_kept"] for v in two["videos"]}
    assert kept == {"a": 1, "b": 0} and two["removed_examples"][0]["duplicate_of"]["source_id"] == "a"
    assert clean_documents([_doc("a", ["Yes that is right.", "Yes that is right."])])["videos"][0]["quality"]["segments_kept"] == 2


def test_low_confidence_is_flagged_not_removed():
    video = clean_documents([_doc("a", [GLITCH, "Another clear sentence about the moon and tides today."], confs={0: 0.3})])["videos"][0]
    assert [s["low_confidence"] for s in video["segments"]] == [True, False]
    assert video["quality"]["low_confidence_segments"] == 1


def test_a_trained_model_replaces_the_rule_in_the_output(small_training):
    docs = _content_docs()
    sentences, words, duplicates, report = training.train_all(docs)
    line = "Join the channel by hitting subscribe right now."
    page = [_doc("a", [line, "The telescope collects faint light from distant galaxies across the universe."])]
    assert clean_documents(page)["videos"][0]["quality"]["segments_kept"] == 2  # the rule list does not know this phrasing
    used = Cleaner(sentences, None, None)
    out = clean_documents(page, used)
    assert out["videos"][0]["quality"]["segments_kept"] == 1 and out["cleaning"]["trained_models_in_use"]["sentences"] is True


# ------------------------------------------------------------------ the API
class _Repo:
    def __init__(self, docs):
        self.docs = docs

    async def list_transcripts(self, source_ids=None):
        return [d for d in self.docs if not source_ids or d["source_id"] in source_ids]


class _Transcriber:
    cfg = AsrConfig("fake", "cpu", "int8", 8, 5)


def _client(tmp_path, docs):
    app = create_app()
    app.state.repo, app.state.transcriber = _Repo(docs), _Transcriber()
    settings = Settings(data_dir=tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_summary_and_download_endpoints(tmp_path):
    with _client(tmp_path, [_doc("a", [GLITCH, GLITCH])]) as c:
        s = c.get("/api/cleaning/summary").json()
        assert s["summary"]["segments_kept"] == 1 and "segments" not in s["videos"][0]
        assert set(s["reasons"]) == {"too_short", "duplicate_in_video", "duplicate_across_videos"}
        d = c.get("/api/cleaning/download")
        assert "attachment" in d.headers["content-disposition"] and d.json()["videos"][0]["segments"][0]["id"] == 0
    with _client(tmp_path, []) as c:
        assert c.get("/api/cleaning/summary").status_code == 404


def test_training_endpoint_saves_the_models_and_the_json_uses_them(small_training, tmp_path):
    with _client(tmp_path, _content_docs()) as c:
        assert c.get("/api/cleaning/model").json() == {"report": None, "in_use": {"sentences": False, "words": False, "duplicates": False}}
        trained = c.post("/api/cleaning/train").json()
        report = trained["report"]
        assert {k for k in report if k in ("sentences", "words", "duplicates")} == {"sentences", "words", "duplicates"}
        assert trained["in_use"] == {"sentences": report["sentences"]["activated"], "words": report["words"]["activated"],
                                     "duplicates": report["duplicates"]["activated"]}
        assert (tmp_path / "models" / "cleaning" / "report.json").exists()
        out = c.get("/api/cleaning/download").json()
        assert out["cleaning"]["trained_models_in_use"] == trained["in_use"]
        assert out["cleaning"]["model_test_results"]["real_sentences"] == report["real_sentences"]
    with _client(tmp_path / "x", []) as c:
        assert c.post("/api/cleaning/train").status_code == 404
    with _client(tmp_path / "y", _content_docs(n_docs=1, n=10)) as c:
        assert c.post("/api/cleaning/train").status_code == 422


def test_models_are_saved_and_loaded_back_identically(small_training, tmp_path):
    sentences, words, duplicates, report = training.train_all(_content_docs())
    cleaner_store.save(tmp_path, sentences, words, duplicates, report)
    loaded = cleaner_store.load_cleaner(tmp_path)
    assert loaded.in_use == {"sentences": report["sentences"]["activated"], "words": report["words"]["activated"],
                             "duplicates": report["duplicates"]["activated"]}
    text = "So um, the telescope collects faint light, you know, every few hours. Thanks for watching."
    assert loaded.clean_text(text) == training.cleaner_from(sentences, words, duplicates, report).clean_text(text)
    assert np.isclose(float(words.weights.sum()), float(word_model.WordModel.from_json(words.to_json()).weights.sum()), atol=1e-2)
