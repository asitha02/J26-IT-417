"""
Tests for the separation helpers (the Demucs model itself is not loaded here: too slow for unit tests;
it is checked with scripts/test_separation.py on a real video).
Run from the c4-audio-emotion folder:  venv\Scripts\python -m pytest
"""
import numpy as np

from backend.separation import NoSeparation, _match_length, combine_sources


def test_speech_is_vocals_and_background_is_everything_else():
    n = 10
    sources = {"drums": np.full(n, 0.1), "bass": np.full(n, 0.2), "other": np.full(n, 0.3), "vocals": np.full(n, 0.5)}
    speech, background = combine_sources(sources)
    assert np.allclose(speech, 0.5)
    assert np.allclose(background, 0.6)          # 0.1 + 0.2 + 0.3


def test_tracks_are_matched_to_the_original_length():
    assert len(_match_length(np.ones(12), 10)) == 10
    padded = _match_length(np.ones(8), 10)
    assert len(padded) == 10 and padded[-1] == 0  # padded with silence


def test_no_separation_returns_mixed_audio_as_background():
    audio = np.arange(5, dtype=float)
    speech, background = NoSeparation().separate(audio)
    assert np.array_equal(background, audio) and not speech.any()
