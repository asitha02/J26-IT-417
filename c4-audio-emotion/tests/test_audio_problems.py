"""
Tests for the measured audio problems (synthetic tones/noise, no internet needed).
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
import numpy as np

from backend.audio_problems import detect_problems, loudness_db, window_metrics
from backend.config import SAMPLE_RATE


def tone(seconds, amplitude):
    """A steady sine tone: easy to reason about (RMS = amplitude / sqrt(2))."""
    t = np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE
    return (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def test_loudness_of_known_signals():
    assert abs(loudness_db(tone(1, 1.0)) - (-3.0)) < 0.1      # full-scale sine = -3 dB
    assert abs(loudness_db(tone(1, 0.1)) - (-23.0)) < 0.1     # 10x quieter = 20 dB lower
    assert loudness_db(np.zeros(100)) < -150                  # silence, no crash


def test_quiet_music_under_speech_is_fine():
    speech, music = tone(60, 0.3), tone(60, 0.03)             # music 20 dB below speech
    problems = detect_problems(window_metrics(speech + music, speech, music))
    assert not [p for p in problems if p["type"] == "music_too_loud"]


def test_music_almost_as_loud_as_speech_is_high_severity():
    speech, music = tone(60, 0.3), tone(60, 0.25)             # music only ~1.6 dB below speech
    p = [p for p in detect_problems(window_metrics(speech + music, speech, music)) if p["type"] == "music_too_loud"]
    assert len(p) == 1 and p[0]["severity"] == "high"
    assert (p[0]["start_s"], p[0]["end_s"]) == (0, 60)


def test_no_speech_means_no_music_loudness_problem():
    music = tone(60, 0.5)                                     # e.g. an intro with music only
    metrics = window_metrics(music, np.zeros_like(music), music)
    assert all(w["music_minus_speech_db"] is None for w in metrics)
    assert not detect_problems(metrics)


def test_clipping_is_detected():
    loud = np.clip(tone(30, 2.0), -1, 1)                      # driven past the maximum -> flat tops
    p = detect_problems(window_metrics(loud, np.zeros_like(loud), loud))
    assert [x["type"] for x in p] == ["clipping"]


def test_dead_air_is_detected_only_when_long_enough():
    audio = np.concatenate([tone(20, 0.3), np.zeros(25 * SAMPLE_RATE, np.float32), tone(20, 0.3)])
    p = [x for x in detect_problems(window_metrics(audio, audio, np.zeros_like(audio))) if x["type"] == "silence"]
    assert len(p) == 1 and p[0]["severity"] == "low"
