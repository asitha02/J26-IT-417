"""
Automatic tests for the fusion rules.
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
from backend.audio_utils import make_segment_times
from backend.fusion import find_runs, generate_recommendations


def timeline(low_windows: set) -> list[dict]:
    """A 3-minute timeline: arousal -0.6 for window numbers in low_windows, 0.2 elsewhere."""
    segs = make_segment_times(180)
    for i, s in enumerate(segs):
        s["valence"] = 0.1
        s["arousal"] = -0.6 if i in low_windows else 0.2
    return segs


def test_find_runs_groups_consecutive_items():
    items = [{"v": x} for x in [0, 1, 1, 0, 1]]
    runs = find_runs(items, lambda s: s["v"] == 1)
    assert [len(r) for r in runs] == [2, 1]


def test_r1_long_low_energy_section_is_reported():
    recs = generate_recommendations(timeline(set(range(20, 28))))  # 100 s -> 145 s
    assert len(recs) == 1
    rec = recs[0]
    assert rec["rule_id"] == "R1_low_energy"
    assert (rec["start_s"], rec["end_s"]) == (100, 145)
    assert rec["id"] == "rec_001"
    assert rec["evidence"]                                          # never empty


def test_r1_short_dip_is_ignored():
    assert generate_recommendations(timeline({3, 4})) == []        # only 15 s


def test_r1_nothing_on_energetic_audio():
    assert generate_recommendations(timeline(set())) == []
