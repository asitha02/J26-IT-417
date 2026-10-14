"""
Automatic tests for audio_utils (no internet needed: fake audio made with numpy).
Run from the c4-audio-emotion folder:  venv\\Scripts\\python -m pytest
"""
import numpy as np
import pytest

from backend.audio_utils import cut_segments, extract_video_id, make_segment_times
from backend.config import SAMPLE_RATE, SEGMENT_SECONDS

VID = "jNQXAC9IVRw"


# ---------- extract_video_id ----------

@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={VID}",
    f"https://youtube.com/watch?v={VID}&t=30s",
    f"https://m.youtube.com/watch?v={VID}",
    f"https://youtu.be/{VID}",
    f"https://youtu.be/{VID}?si=abc",
    f"https://www.youtube.com/shorts/{VID}",
])
def test_valid_urls_give_video_id(url):
    assert extract_video_id(url) == VID


@pytest.mark.parametrize("url", [
    "",
    "not a url",
    f"https://evil.com/watch?v={VID}",        # right id, wrong website
    "https://www.youtube.com/watch?v=short",  # id is not 11 characters
    "https://www.youtube.com/",               # no id at all
])
def test_invalid_urls_give_none(url):
    assert extract_video_id(url) is None


# ---------- make_segment_times ----------

def test_three_minutes_gives_35_windows():
    times = make_segment_times(180)
    assert len(times) == 35
    assert times[0] == {"start_s": 0, "end_s": 10}
    assert times[1] == {"start_s": 5, "end_s": 15}      # 5 s hop
    assert times[-1] == {"start_s": 170, "end_s": 180}


def test_long_video_is_capped_at_three_minutes():
    assert make_segment_times(4600) == make_segment_times(180)


def test_audio_shorter_than_one_window():
    assert make_segment_times(7) == [{"start_s": 0, "end_s": 7}]


def test_last_window_ends_at_audio_end():
    times = make_segment_times(19)
    assert times[-1] == {"start_s": 10, "end_s": 19}


# ---------- cut_segments ----------

def fake_audio(seconds: float) -> np.ndarray:
    return np.random.default_rng(0).uniform(-1, 1, int(seconds * SAMPLE_RATE)).astype(np.float32)


def test_every_window_has_the_same_length():
    for seg in cut_segments(fake_audio(23)):
        assert seg["audio"].shape == (SEGMENT_SECONDS * SAMPLE_RATE,)


def test_short_last_window_is_padded_with_silence():
    audio = fake_audio(23)                   # windows ..., 15-23 -> 8 s real + 2 s silence
    last = cut_segments(audio)[-1]
    real = 8 * SAMPLE_RATE
    assert np.array_equal(last["audio"][:real], audio[15 * SAMPLE_RATE:])
    assert np.all(last["audio"][real:] == 0)


def test_window_audio_matches_its_time():
    audio = fake_audio(30)
    seg = cut_segments(audio)[1]             # 5-15 s
    assert np.array_equal(seg["audio"], audio[5 * SAMPLE_RATE:15 * SAMPLE_RATE])
