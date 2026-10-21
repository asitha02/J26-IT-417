import pytest

from tools.asr_benchmark import normalize, recommend, wer


def test_normalize_ignores_case_and_punctuation():
    assert normalize("Hello, World! It's a well-known fact.") == ["hello", "world", "it's", "a", "well", "known", "fact"]


def test_wer_counts_substitution_deletion_insertion():
    assert wer("the cat sat", "the cat sat") == 0
    assert wer("the cat sat", "the dog sat") == pytest.approx(1 / 3)       # substitution
    assert wer("the cat sat", "the sat") == pytest.approx(1 / 3)           # deletion
    assert wer("the cat sat", "the big cat sat") == pytest.approx(1 / 3)   # insertion
    assert wer("a b c d", "") == 1.0
    with pytest.raises(ValueError):
        wer("", "anything")


def test_recommend_picks_fastest_within_tolerance():
    rows = [
        {"model": "small.en", "wer": 0.050, "rtf": 0.40},
        {"model": "distil-small.en", "wer": 0.055, "rtf": 0.20},   # within 1 point of best -> eligible
        {"model": "base.en", "wer": 0.090, "rtf": 0.08},           # fastest but too inaccurate
    ]
    assert recommend(rows, 0.01)["model"] == "distil-small.en"
    assert recommend(rows, 0.0)["model"] == "small.en"
