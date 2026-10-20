"""
Tests for the dummy-data loader.
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
from backend.mock_loader import load_c3_sentiment, load_knowledge_gaps

C3_FIELDS = {"video_id", "sentiment_score", "sentiment_label", "comment_count",
             "top_complaints", "requested_topics", "timestamped_feedback"}


def test_known_videos_get_their_own_variant():
    assert load_c3_sentiment("xCUKEqa8MKQ")["variant"] == "negative"
    assert load_c3_sentiment("vbZKydfBUUI")["variant"] == "mixed"
    assert load_c3_sentiment("jNQXAC9IVRw")["variant"] == "positive"


def test_unknown_video_falls_back_to_default():
    c3 = load_c3_sentiment("UNKNOWN0000")
    assert c3["variant"] == "default"
    assert c3["video_id"] == "UNKNOWN0000"        # labelled with the requested video
    assert load_knowledge_gaps("UNKNOWN0000")["gaps"]


def test_dummy_data_is_always_marked_and_follows_the_contract():
    c3 = load_c3_sentiment("xCUKEqa8MKQ")
    assert c3["mock"] is True and load_knowledge_gaps("xCUKEqa8MKQ")["mock"] is True
    assert C3_FIELDS <= set(c3)
    for comment in c3["timestamped_feedback"]:
        assert 0 <= comment["t_s"] <= 180 and -1 <= comment["sentiment"] <= 1


def test_loading_twice_does_not_leak_changes():
    load_c3_sentiment("AAAAAAAAAAA")
    assert load_c3_sentiment("BBBBBBBBBBB")["video_id"] == "BBBBBBBBBBB"


def test_c1_sections_follow_the_contract():
    from backend.mock_loader import load_c1_transcript
    for vid in ["e-P5IFTqB98", "UNKNOWN0000"]:
        c1 = load_c1_transcript(vid)
        assert c1["mock"] is True and c1["sections"]
        for sec in c1["sections"]:
            assert sec["content_type"] in {"hook", "explanation", "example", "summary"}
            assert 0 <= sec["start_s"] < sec["end_s"] <= 180
