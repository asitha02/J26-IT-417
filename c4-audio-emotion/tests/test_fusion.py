"""
Automatic tests for the fusion rules R1-R6 (made-up timelines, no internet or database needed).
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
from backend.audio_utils import make_segment_times
from backend.fusion import (
    confidence,
    find_runs,
    generate_recommendations,
    merge_overlapping,
    rule_r1_low_energy,
    rule_r2_tense_audio,
    rule_r3_flat_profile,
    rule_r4_complex_content_audio,
    rule_r5_audio_complaints,
    rule_r6_requested_topics,
)


def timeline(arousal_for, valence_for=lambda i: 0.1) -> list[dict]:
    """A 3-minute timeline (35 windows); arousal/valence chosen per window number i."""
    segs = make_segment_times(180)
    for i, s in enumerate(segs):
        s["arousal"], s["valence"] = arousal_for(i), valence_for(i)
    return segs


def varied(i):
    """A lively arousal pattern (high variance) so R3 doesn't fire by accident."""
    return [0.5, -0.1, 0.3, 0.0][i % 4]


NO_C3 = {}
NEG_C3 = {
    "sentiment_score": -0.5, "comment_count": 100,
    "top_complaints": ["music too loud", "slow pacing", "bad thumbnail"],
    "requested_topics": ["Hawking radiation", "neutron stars"],
    "timestamped_feedback": [{"t_s": 120, "text": "this part drags", "sentiment": -0.6},
                             {"t_s": 20, "text": "great intro", "sentiment": 0.8}],
}
GAPS = {"gaps": [{"topic": "Hawking radiation", "start_s": 120, "end_s": 165, "severity": "medium",
                  "description": "not explained"}]}


# ---------- helpers ----------

def test_find_runs_groups_consecutive_items():
    runs = find_runs([{"v": x} for x in [0, 1, 1, 0, 1]], lambda s: s["v"] == 1)
    assert [len(r) for r in runs] == [2, 1]


def test_confidence_grows_with_evidence_and_is_capped():
    assert confidence(0) == 0.5
    assert confidence(1) == 0.7
    assert confidence(10) == 0.95


# ---------- R1 low energy ----------

LOW_100_145 = lambda i: -0.6 if 20 <= i <= 27 else varied(i)   # windows 100 s -> 145 s


def test_r1_long_low_energy_section_is_reported():
    recs = rule_r1_low_energy(timeline(LOW_100_145), NO_C3)
    assert len(recs) == 1
    assert (recs[0]["start_s"], recs[0]["end_s"]) == (100, 145)
    assert recs[0]["severity"] == "medium" and recs[0]["confidence"] == 0.5


def test_r1_becomes_high_with_nearby_negative_comment():
    rec = rule_r1_low_energy(timeline(LOW_100_145), NEG_C3)[0]
    assert rec["severity"] == "high"
    assert rec["confidence"] == 0.7
    assert any("this part drags" in e for e in rec["evidence"])
    assert not any("great intro" in e for e in rec["evidence"])     # positive / far-away comment ignored


def test_r1_detects_a_small_dip_in_a_near_neutral_video():
    # Like real science videos: arousal around +0.10, dipping to +0.03 for 30 s (100 s -> 130 s).
    # The old absolute rule (arousal < -0.3) would never fire here; the relative rule does.
    recs = rule_r1_low_energy(timeline(lambda i: 0.03 if 20 <= i <= 24 else 0.10), NO_C3)
    assert [(r["start_s"], r["end_s"]) for r in recs] == [(100, 130)]
    assert "calmer here than in the rest of the video" in recs[0]["evidence"][0]


def test_rules_judge_each_video_against_itself():
    # Same shape, whole video shifted up by 0.4 -> exactly the same recommendations.
    shape = lambda i: 0.03 if 20 <= i <= 24 else 0.10
    low = rule_r1_low_energy(timeline(shape), NO_C3)
    high = rule_r1_low_energy(timeline(lambda i: shape(i) + 0.4), NO_C3)
    assert [(r["start_s"], r["end_s"]) for r in low] == [(r["start_s"], r["end_s"]) for r in high]


def test_r1_short_dip_is_ignored():
    assert rule_r1_low_energy(timeline(lambda i: -0.6 if i in (3, 4) else varied(i)), NO_C3) == []


# ---------- R2 tense audio ----------

def test_r2_tense_section_reported_and_high_with_audio_complaint():
    segs = timeline(lambda i: 0.8 if 10 <= i <= 14 else varied(i),
                    lambda i: -0.6 if 10 <= i <= 14 else 0.1)            # 50 s -> 80 s
    assert rule_r2_tense_audio(segs, NO_C3)[0]["severity"] == "medium"
    rec = rule_r2_tense_audio(segs, NEG_C3)[0]
    assert rec["severity"] == "high"
    assert any("music too loud" in e for e in rec["evidence"])


def test_r2_needs_both_high_arousal_and_negative_valence():
    segs = timeline(lambda i: 0.8, lambda i: 0.5)                        # energetic but positive
    assert rule_r2_tense_audio(segs, NO_C3) == []


# ---------- R3 flat profile ----------

def test_r3_flat_energy_is_reported():
    recs = rule_r3_flat_profile(timeline(lambda i: 0.1), 180)
    assert len(recs) == 1 and recs[0]["severity"] == "low"


def test_r3_varied_energy_is_fine():
    assert rule_r3_flat_profile(timeline(varied), 180) == []


def test_r3_needs_enough_windows_to_judge():
    short = make_segment_times(19)                     # only 3 windows
    for s in short:
        s["arousal"], s["valence"] = 0.1, 0.0
    assert rule_r3_flat_profile(short, 19) == []


# ---------- R4 intense audio over complex content ----------

def test_r4_gap_with_intense_audio_is_reported():
    segs = timeline(lambda i: 0.7 if 24 <= i <= 30 else -0.1)             # intense 120 s -> 160 s
    rec = rule_r4_complex_content_audio(segs, GAPS, NO_C3)[0]
    assert (rec["start_s"], rec["end_s"]) == (120, 165)
    assert rec["confidence"] == 0.7                                       # audio + gap
    assert any("Hawking radiation" in e for e in rec["evidence"])


def test_r4_calm_audio_during_gap_is_fine():
    assert rule_r4_complex_content_audio(timeline(lambda i: 0.0), GAPS, NO_C3) == []


# ---------- R5 audio complaints ----------

def test_r5_negative_audience_with_audio_complaints():
    rec = rule_r5_audio_complaints(NEG_C3, 180)[0]
    complaints = [e for e in rec["evidence"] if e.startswith("Complaint")]
    assert len(complaints) == 2                                           # "bad thumbnail" is not audio
    assert rec["confidence"] == 0.7


def test_r5_not_triggered_when_audience_is_positive():
    assert rule_r5_audio_complaints({**NEG_C3, "sentiment_score": 0.4}, 180) == []


# ---------- R6 requested topics ----------

def test_r6_only_lists_topics_the_video_does_not_cover():
    rec = rule_r6_requested_topics(NEG_C3, GAPS, 180)[0]
    assert rec["evidence"] == ["Requested topic: 'neutron stars'"]        # Hawking radiation is a gap topic


# ---------- combining ----------

def test_merge_overlapping_same_type():
    a = {"type": "x", "start_s": 0, "end_s": 30, "severity": "medium", "confidence": 0.5, "evidence": ["a"]}
    b = {"type": "x", "start_s": 20, "end_s": 50, "severity": "high", "confidence": 0.7, "evidence": ["b"]}
    merged = merge_overlapping([a, b])
    assert len(merged) == 1
    assert (merged[0]["start_s"], merged[0]["end_s"], merged[0]["severity"]) == (0, 50, "high")
    assert merged[0]["evidence"] == ["a", "b"]


def test_full_run_is_sorted_numbered_and_explained():
    recs = generate_recommendations(timeline(LOW_100_145), NEG_C3, GAPS, 180)
    order = {"high": 0, "medium": 1, "low": 2}
    assert [order[r["severity"]] for r in recs] == sorted(order[r["severity"]] for r in recs)
    assert [r["id"] for r in recs] == [f"rec_{i:03d}" for i in range(1, len(recs) + 1)]
    assert all(r["evidence"] for r in recs)                               # never a black box
    assert {"R1_low_energy", "R5_audio_complaints", "R6_requested_topics"} <= {r["rule_id"] for r in recs}


def test_nothing_on_a_healthy_video():
    happy = {"sentiment_score": 0.6, "top_complaints": [], "requested_topics": [], "timestamped_feedback": []}
    assert generate_recommendations(timeline(varied), happy, {"gaps": []}, 180) == []


# ---------- Part 2 rules using C1 sections and measured audio problems ----------

from backend.fusion import rule_r7_mood_content_mismatch, rule_r8_music_too_loud, rule_r9_audio_quality, video_link

C1 = {"sections": [
    {"start_s": 0, "end_s": 30, "topic": "intro", "content_type": "hook"},
    {"start_s": 120, "end_s": 165, "topic": "Hawking radiation", "content_type": "explanation"},
]}
LOUD = {"type": "music_too_loud", "severity": "medium", "start_s": 110, "end_s": 140,
        "description": "too loud", "evidence": ["At its loudest the music is only 5 dB quieter than the voice"]}


def test_r7_lively_music_during_an_explanation():
    segs = timeline(lambda i: 0.4 if 23 <= i <= 31 else 0.0)            # livelier from 115 s on
    recs = rule_r7_mood_content_mismatch(segs, C1, NO_C3)
    lively = [r for r in recs if r["title"] == "Music is too lively for the explanation of 'Hawking radiation'"]
    assert len(lively) == 1 and (lively[0]["start_s"], lively[0]["end_s"]) == (120, 165)
    assert lively[0]["confidence"] == 0.7                                 # audio + transcript agree


def test_r7_calm_opening_hook():
    segs = timeline(lambda i: -0.3 if i <= 4 else 0.1)                  # calm first 30 s
    recs = rule_r7_mood_content_mismatch(segs, C1, NO_C3)
    calm = [r for r in recs if "opening music is calmer" in r["title"]]
    assert len(calm) == 1 and (calm[0]["start_s"], calm[0]["end_s"]) == (0, 30)


def test_r7_fitting_music_gives_no_mismatch():
    assert rule_r7_mood_content_mismatch(timeline(lambda i: 0.1), C1, NO_C3) == []


def test_r8_measured_loud_music_is_raised_by_complaints_and_comments():
    assert rule_r8_music_too_loud([LOUD], NO_C3)[0]["severity"] == "medium"
    rec = rule_r8_music_too_loud([LOUD], NEG_C3)[0]                     # "music too loud" complaint + comment at 120 s
    assert rec["severity"] == "high" and rec["confidence"] == 0.9
    assert any("music too loud" in e for e in rec["evidence"])


def test_r5_is_supported_by_a_measured_problem():
    rec = rule_r5_audio_complaints(NEG_C3, 180, [LOUD])[0]
    assert rec["severity"] == "high"
    assert any(e.startswith("Measured in the audio") for e in rec["evidence"])


def test_r9_turns_clipping_and_silence_into_recommendations():
    problems = [{**LOUD, "type": "clipping"}, {**LOUD, "type": "silence"}]
    assert [r["type"] for r in rule_r9_audio_quality(problems)] == ["distortion", "dead_air"]


def test_every_recommendation_links_to_its_moment_in_the_video():
    url = "https://www.youtube.com/watch?v=ABCDEFGHIJK"
    assert video_link(url, 125) == url + "&t=125s"
    assert video_link(url, 0) == url
    recs = generate_recommendations(timeline(LOW_100_145), NEG_C3, GAPS, 180, C1, [LOUD], url)
    assert all(r["link"].startswith(url) for r in recs)
    assert {"R7_mood_content_mismatch", "R8_music_too_loud"} & {r["rule_id"] for r in recs}


def test_r4_and_r7_on_the_same_explanation_become_one_card():
    segs = timeline(lambda i: 0.4 if 24 <= i <= 31 else 0.0)            # lively during 120-165 s
    recs = generate_recommendations(segs, NO_C3, GAPS, 180, C1)
    same_place = [r for r in recs if r["type"] == "intense_audio_complex_content"]
    assert len(same_place) == 1
    text = " ".join(same_place[0]["evidence"])
    assert "Knowledge gap 'Hawking radiation'" in text and "This part explains 'Hawking radiation'" in text
