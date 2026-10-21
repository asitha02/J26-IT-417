"""
Part 1: measured audio problems (descriptive). No machine learning here: plain loudness
measurements on the tracks from separation.py, so every problem is easy to check and explain.

For every 10 s window (same windows as the emotion timeline):
  speech_db, music_db       loudness of the narration and of the background music
  music_minus_speech_db     how much quieter (negative) or louder (positive) the music is than the speech
  clipping_pct              % of samples at the maximum level (distortion)
  silent                    True if the whole mix is almost silent

Loudness = RMS (root mean square: the average energy of the samples) in dB.
0 dB is the maximum possible level; -20 dB is 10x lower in amplitude.
"""
import numpy as np

from backend.audio_utils import cut_segments
from backend.config import (
    CLIPPING_PCT,
    MUSIC_LOUD_MIN_DURATION_S,
    MUSIC_NEARLY_AS_LOUD_DB,
    MUSIC_UNDER_SPEECH_LIMIT_DB,
    SILENCE_DB,
    SILENCE_MIN_DURATION_S,
    SPEECH_PRESENT_DB,
)
from backend.fusion import find_runs, mmss


def loudness_db(audio: np.ndarray) -> float:
    """RMS loudness in dB (0 = maximum). Silence gives about -180 dB instead of minus infinity."""
    return float(20 * np.log10(np.sqrt(np.mean(np.square(audio))) + 1e-9))


def window_metrics(mixed: np.ndarray, speech: np.ndarray, music: np.ndarray) -> list[dict]:
    """Loudness measurements for each 10 s window of the three tracks."""
    metrics = []
    for m, s, b in zip(cut_segments(mixed), cut_segments(speech), cut_segments(music)):
        speech_db, music_db = loudness_db(s["audio"]), loudness_db(b["audio"])
        metrics.append({
            "start_s": m["start_s"],
            "end_s": m["end_s"],
            "speech_db": round(speech_db, 1),
            "music_db": round(music_db, 1),
            # Only meaningful while someone speaks; None when there is no speech.
            "music_minus_speech_db": round(music_db - speech_db, 1) if speech_db > SPEECH_PRESENT_DB else None,
            "clipping_pct": round(float(np.mean(np.abs(m["audio"]) >= 0.99) * 100), 3),
            "silent": loudness_db(m["audio"]) < SILENCE_DB,
        })
    return metrics


def _problem(ptype, severity, start, end, description, evidence) -> dict:
    return {"type": ptype, "severity": severity, "start_s": start, "end_s": end,
            "description": description, "evidence": evidence}


def detect_problems(metrics: list[dict]) -> list[dict]:
    """Turn the window measurements into a list of audio problems with plain-language descriptions."""
    problems = []

    # 1. Background music too loud under the narration
    too_loud = lambda w: w["music_minus_speech_db"] is not None and w["music_minus_speech_db"] > MUSIC_UNDER_SPEECH_LIMIT_DB
    for run in find_runs(metrics, too_loud):
        start, end = run[0]["start_s"], run[-1]["end_s"]
        if end - start < MUSIC_LOUD_MIN_DURATION_S:
            continue
        worst = max(w["music_minus_speech_db"] for w in run)
        gap = -worst
        severity = "high" if worst > MUSIC_NEARLY_AS_LOUD_DB else "medium"
        problems.append(_problem(
            "music_too_loud", severity, start, end,
            f"The background sound (music or noise) is too loud under the narration during {mmss(start)}–{mmss(end)}.",
            [f"At its loudest the background is only {gap:.0f} dB quieter than the voice" if gap > 0
             else f"At its loudest the background is {-gap:.0f} dB LOUDER than the voice",
             f"Background music and sounds should stay more than {-MUSIC_UNDER_SPEECH_LIMIT_DB} dB below the voice "
             f"so the narration is easy to follow"],
        ))

    # 2. Distortion (clipping)
    for run in find_runs(metrics, lambda w: w["clipping_pct"] > CLIPPING_PCT):
        start, end = run[0]["start_s"], run[-1]["end_s"]
        problems.append(_problem(
            "clipping", "medium", start, end,
            f"The audio is distorted (clipping) during {mmss(start)}–{mmss(end)}.",
            [f"Up to {max(w['clipping_pct'] for w in run):.2f} % of the sound samples hit the maximum level"],
        ))

    # 3. Dead air
    for run in find_runs(metrics, lambda w: w["silent"]):
        start, end = run[0]["start_s"], run[-1]["end_s"]
        if end - start >= SILENCE_MIN_DURATION_S:
            problems.append(_problem(
                "silence", "low", start, end,
                f"Almost no sound during {mmss(start)}–{mmss(end)} ({end - start:.0f} s of dead air).",
                [f"The whole mix stays below {SILENCE_DB} dB"],
            ))

    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(problems, key=lambda p: (order[p["severity"]], p["start_s"]))
