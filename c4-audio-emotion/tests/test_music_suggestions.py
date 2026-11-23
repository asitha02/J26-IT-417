"""
Tests for the background music suggestions (backend/music_suggestions.py). No internet needed.
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
from backend.music_suggestions import TAG_MOOD, load_catalog, suggest_music, tag_mood, target_mood

EXPLANATION_VIDEO = {"sections": [{"start_s": 0, "end_s": 20, "content_type": "hook"},
                                  {"start_s": 20, "end_s": 180, "content_type": "explanation"}]}


def test_catalog_is_valid():
    catalog = load_catalog()
    assert len(catalog) >= 10
    for t in catalog:
        assert t["url"].startswith("https://")
        assert t["source"] in ("incompetech", "pixabay")
        assert t["license"] in ("CC BY 4.0", "Pixabay Content License")
        assert all(tag in TAG_MOOD for tag in t["mood_tags"]), t["title"]   # no unknown tags


def test_tag_mood_is_the_average_of_the_tags():
    assert tag_mood(["Calming", "Relaxed"]) == (0.35, -0.55)
    assert tag_mood([]) == (0.0, 0.0)


def test_explanation_heavy_video_targets_calm_positive_music():
    v, a, reasons = target_mood(EXPLANATION_VIDEO, [])
    assert v > 0 and a < 0
    assert "explanation" in reasons[0]


def test_low_energy_problem_makes_the_target_livelier():
    _, calm, _ = target_mood(EXPLANATION_VIDEO, [])
    _, livelier, reasons = target_mood(EXPLANATION_VIDEO, [{"type": "low_energy_segment"}])
    assert livelier > calm
    assert len(reasons) == 2


def test_no_c1_sections_uses_the_default():
    v, a, reasons = target_mood({}, [])
    assert (v, a) == (0.4, -0.2)
    assert "default" in reasons[0]


def test_suggests_five_tracks_from_both_sources_best_first():
    s = suggest_music(EXPLANATION_VIDEO, [])
    tracks = s["tracks"]
    assert len(tracks) == 5
    assert {t["source"] for t in tracks} == {"incompetech", "pixabay"}
    assert [t["match"] for t in tracks] == sorted((t["match"] for t in tracks), reverse=True)
    assert len({t["title"] for t in tracks}) == 5   # no duplicates
    assert s["target_mood"] == "calm and positive"


def test_cc_by_tracks_carry_a_credit_line_and_pixabay_tracks_do_not():
    for t in suggest_music(EXPLANATION_VIDEO, [], count=23)["tracks"]:
        if t["license"] == "CC BY 4.0":
            assert t["attribution_required"] and "Kevin MacLeod" in t["credit"]
        else:
            assert not t["attribution_required"] and t["credit"] == ""


def test_loud_music_problem_changes_the_mixing_tip():
    s = suggest_music(EXPLANATION_VIDEO, [{"type": "music_too_loud"}])
    assert "flagged as too loud" in s["mixing_tip"]
