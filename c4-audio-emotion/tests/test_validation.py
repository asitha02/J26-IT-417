"""
Tests for the segment-level validation against audience comments.
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
from backend.validation import chance_of_hit, validate


def rec(start, end):
    return {"start_s": start, "end_s": end}


C3 = {"mock": True, "timestamped_feedback": [
    {"t_s": 12, "sentiment": -0.7},     # negative
    {"t_s": 95, "sentiment": -0.5},     # negative
    {"t_s": 140, "sentiment": 0.9},     # positive: ignored
]}


def test_agreement_counts_flags_near_negative_comments():
    v = validate([rec(0, 20), rec(80, 115), rec(150, 170)], C3, 180)
    assert (v["flagged_segments"], v["agreeing_segments"]) == (3, 2)
    assert v["agreement"] == round(2 / 3, 3)
    assert (v["negative_comments"], v["comments_explained"]) == (2, 2)
    assert v["mock_data"] is True


def test_whole_video_recommendations_are_not_counted():
    v = validate([rec(0, 180), rec(80, 115)], C3, 180)
    assert v["flagged_segments"] == 1


def test_random_baseline_is_exact_for_a_simple_case():
    # One comment at 100 s, ranges of 10 s, window ±15 s -> hits when start is in [75, 115]: 41 of 171 starts.
    assert chance_of_hit(10, 180, [100]) == 41 / 171


def test_lift_above_one_when_flags_beat_chance():
    v = validate([rec(80, 100)], C3, 180)
    assert v["lift"] > 1 and v["random_baseline"] < 1


def test_no_comments_or_no_flags_give_clear_messages():
    assert validate([], C3, 180)["agreement"] is None
    v = validate([rec(80, 100)], {"timestamped_feedback": []}, 180)
    assert v["lift"] is None and "no negative viewer comments" in v["explanation"]
