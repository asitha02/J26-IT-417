"""
Emotion models: turn audio segments into valence/arousal values.

Both models have the same predict() method, so main.py does not care which
one it uses (chosen by USE_MOCK_MODEL in .env):
  - MockEmotionModel: fake but smooth values, to test the pipeline end to end.
  - RealEmotionModel: CLAP embeddings + my trained BiLSTM+attention head (Day 10).

Valence = how negative (-1) or positive (+1) the audio feels.
Arousal = how calm (-1) or energetic (+1) the audio feels.
"""
import random

MOCK_MODEL_INFO = {"embedding_model": "none", "head": "mock_random_walk", "mock": True}


class MockEmotionModel:
    """Fake values: a 'random walk' that drifts a little at each segment."""

    info = MOCK_MODEL_INFO

    def predict(self, segments_audio: list[dict], video_id: str = "") -> list[dict]:
        """
        segments_audio: [{'start_s', 'end_s', ...}, ...] (audio itself is ignored here)
        video_id: used as the random seed, so the same video always gets the same values.
        Returns [{'start_s', 'end_s', 'valence', 'arousal'}, ...]
        """
        rng = random.Random(video_id)
        valence = rng.uniform(-0.5, 0.5)
        arousal = rng.uniform(-0.5, 0.5)

        results = []
        for seg in segments_audio:
            # Small random step each time -> a smooth, realistic-looking curve.
            valence = _clip(valence + rng.gauss(0, 0.15))
            arousal = _clip(arousal + rng.gauss(0, 0.15))
            results.append({
                "start_s": seg["start_s"],
                "end_s": seg["end_s"],
                "valence": round(valence, 3),
                "arousal": round(arousal, 3),
            })
        return results


def get_model(use_mock: bool):
    """Pick the model based on the USE_MOCK_MODEL setting."""
    if use_mock:
        return MockEmotionModel()
    raise NotImplementedError("RealEmotionModel is added on Day 10. Set USE_MOCK_MODEL=true.")


# ---------- helpers used after prediction ----------

def _clip(x: float) -> float:
    """Keep a value inside [-1, 1]."""
    return max(-1.0, min(1.0, x))


def quadrant_of(valence: float, arousal: float) -> str:
    """
    Name the area of the valence-arousal plane (Russell's circumplex) a point falls in.
    Zero counts as positive / energetic.
    """
    if valence >= 0 and arousal >= 0:
        return "energetic_positive"
    if valence < 0 and arousal >= 0:
        return "tense_negative"
    if valence < 0 and arousal < 0:
        return "low_negative"
    return "calm_positive"


def summarize(segments: list[dict]) -> dict:
    """Mean valence/arousal and the most common quadrant across all segments."""
    n = len(segments)
    quadrants = [s["quadrant"] for s in segments]
    return {
        "mean_valence": round(sum(s["valence"] for s in segments) / n, 3),
        "mean_arousal": round(sum(s["arousal"] for s in segments) / n, 3),
        "dominant_quadrant": max(set(quadrants), key=quadrants.count),
    }
