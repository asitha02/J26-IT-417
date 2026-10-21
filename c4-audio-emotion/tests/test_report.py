"""
Test of the whole Part 2 report built from a synthetic Part 1 result (no internet, no database).
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
import numpy as np

from backend.audio_analysis import run_audio_analysis
from backend.config import SAMPLE_RATE
from backend.mock_loader import load_c1_transcript, load_c3_sentiment, load_knowledge_gaps
from backend.model import MockEmotionModel
from backend.report import build_report
from backend.schemas import RecommendationReport


class LoudMusicSeparator:
    """Speech and music almost equally loud for the first 20 s, then music 20 dB lower."""
    info = {"method": "fake"}

    def separate(self, audio, on_progress=None):
        t = np.arange(len(audio)) / SAMPLE_RATE
        speech = 0.3 * np.sin(2 * np.pi * 200 * t)
        music = np.where(t < 20, 0.28, 0.03) * np.sin(2 * np.pi * 440 * t)
        return speech.astype(np.float32), music.astype(np.float32)


def make_report(video_id="e-P5IFTqB98"):
    audio = np.random.default_rng(1).uniform(-0.2, 0.2, 180 * SAMPLE_RATE).astype(np.float32)
    analysis = run_audio_analysis(video_id, "Demo", audio, MockEmotionModel(), LoudMusicSeparator())
    return build_report(analysis, load_c1_transcript(video_id), load_knowledge_gaps(video_id), load_c3_sentiment(video_id))


def test_report_matches_the_contract_and_is_marked_dummy():
    report = make_report()
    RecommendationReport(**report)                                    # raises if a field is missing or wrong
    assert all(report["inputs"][k]["mock"] for k in ("c1_input", "c2_input", "c3_input"))
    assert report["validation"]["mock_data"] is True


def test_one_summary_per_transcript_section():
    report = make_report()
    assert [s["topic"] for s in report["section_summaries"]][0] == "what happens when a giant star dies"
    intro = report["section_summaries"][0]
    assert "too loud" in intro["music_loudness"] or "LOUDER" in intro["music_loudness"]
    assert intro["negative_comments"] == 1                            # "can barely hear him over the music"


def test_measured_loud_intro_becomes_a_supported_recommendation():
    recs = make_report()["recommendations"]
    loud = [r for r in recs if r["rule_id"] == "R8_music_too_loud"]
    assert loud and loud[0]["severity"] == "high"                     # complaint + comment agree with the measurement
    assert loud[0]["link"].startswith("https://www.youtube.com/watch?v=e-P5IFTqB98")
