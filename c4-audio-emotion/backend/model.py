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

import numpy as np

from backend.config import SAMPLE_RATE

CLAP_MODEL_NAME = "laion/clap-htsat-unfused"
MOCK_MODEL_INFO = {"embedding_model": "none", "head": "mock_random_walk", "mock": True}


class ClapEmbedder:
    """
    Turns each 10 s audio window into an "embedding": a list of 512 numbers
    that summarises what the audio sounds like. Similar-sounding audio gets
    similar numbers. CLAP was pretrained by LAION on a huge set of audio + text
    pairs; we only USE it (frozen: its weights are never changed).

    My trained BiLSTM+attention head (Day 10) reads these 512-number vectors
    instead of raw audio. That is why this step comes before the emotion head.
    """

    def __init__(self):
        # Imported here (not at the top) so the mock model still starts quickly
        # without loading PyTorch and the 600 MB CLAP model.
        import torch
        from transformers import ClapModel, ClapProcessor

        self.torch = torch
        self.processor = ClapProcessor.from_pretrained(CLAP_MODEL_NAME)
        self.model = ClapModel.from_pretrained(CLAP_MODEL_NAME).eval()  # eval = inference mode

    def embed(self, segments_audio: list[dict], batch_size: int = 8) -> np.ndarray:
        """
        segments_audio: [{'audio': np.ndarray of 480 000 samples, ...}, ...]
        Returns an array of shape (number_of_windows, 512).
        Windows are processed in small batches so memory use stays low.
        """
        embeddings = []
        for i in range(0, len(segments_audio), batch_size):
            batch = [s["audio"] for s in segments_audio[i:i + batch_size]]
            # The feature extractor turns raw audio into a mel spectrogram (a picture of
            # which frequencies are loud over time), the input CLAP was trained on.
            inputs = self.processor.feature_extractor(batch, sampling_rate=SAMPLE_RATE, return_tensors="pt")
            with self.torch.no_grad():  # no_grad = don't track gradients: we are not training CLAP
                output = self.model.get_audio_features(**inputs)
            # transformers 5 wraps the result; the 512-number vectors are in pooler_output.
            vectors = output if self.torch.is_tensor(output) else output.pooler_output
            embeddings.append(vectors.numpy())
        return np.concatenate(embeddings, axis=0)


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
