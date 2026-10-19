"""
End-to-end test of Part 1 with synthetic audio, the mock model and no separation
(no internet, no database). Checks the result has the agreed shape (CLAUDE.md 8.6).
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
import numpy as np

from backend.audio_analysis import run_audio_analysis
from backend.config import SAMPLE_RATE
from backend.model import MockEmotionModel
from backend.schemas import AudioAnalysisResponse
from backend.separation import NoSeparation


class FakeSeparator:
    """Pretend separation: 'speech' is a loud tone, 'music' a tone 20 dB quieter."""
    info = {"method": "fake"}

    def separate(self, audio):
        t = np.arange(len(audio)) / SAMPLE_RATE
        speech = 0.3 * np.sin(2 * np.pi * 200 * t)
        music = 0.03 * np.sin(2 * np.pi * 440 * t)
        return speech.astype(np.float32), music.astype(np.float32)


def fake_audio(seconds=60):
    return np.random.default_rng(0).uniform(-0.2, 0.2, seconds * SAMPLE_RATE).astype(np.float32)


def test_part1_result_matches_the_contract():
    result = run_audio_analysis("TESTVIDEO01", "Test video", fake_audio(), MockEmotionModel(), FakeSeparator())
    AudioAnalysisResponse(**result)                       # raises if any field is missing or wrong
    assert len(result["segments"]) == 11                  # 60 s -> 11 windows
    assert result["separation"]["method"] == "fake"
    seg = result["segments"][0]
    assert -21 < seg["music_minus_speech_db"] < -19       # music 20 dB below speech
    assert result["audio_problems"] == []                 # well-mixed, no clipping, no silence


def test_without_separation_the_music_is_the_mixed_audio():
    result = run_audio_analysis("TESTVIDEO02", "Test video", fake_audio(30), MockEmotionModel(), NoSeparation())
    assert result["separation"]["method"] == "none"
    assert all(s["music_minus_speech_db"] is None for s in result["segments"])   # no speech track
    assert result["music_description"] == []              # the mock model can't describe music
