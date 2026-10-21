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
from pathlib import Path

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

    def embed(self, segments_audio: list[dict], batch_size: int = 4) -> np.ndarray:
        """
        segments_audio: [{'audio': np.ndarray of 480 000 samples, ...}, ...]
        Returns an array of shape (number_of_windows, 512).
        Windows are processed in small batches (4 was fastest on a laptop CPU: 3.7 s for 35 windows).
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

    def embed_text(self, texts: list[str]) -> np.ndarray:
        """
        CLAP was trained on audio + TEXT pairs, so it can also turn a description like
        "calm ambient music" into 512 numbers in the same space as the audio embeddings.
        Returns (len(texts), 512), each vector scaled to length 1.
        """
        inputs = self.processor.tokenizer(texts, padding=True, return_tensors="pt")
        with self.torch.no_grad():
            output = self.model.get_text_features(**inputs)
        vectors = (output if self.torch.is_tensor(output) else output.pooler_output).numpy()
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def describe(self, audio_embeddings: np.ndarray, labels: list[str]):
        """
        Zero-shot description: compare each audio embedding with each text label (cosine similarity)
        and turn the similarities into percentages (softmax, using CLAP's own learned temperature).
        Returns (best label per window, overall top 3 as [{"label", "score"}]).
        """
        text = self.embed_text(labels)
        audio = audio_embeddings / np.linalg.norm(audio_embeddings, axis=1, keepdims=True)
        scale = float(self.model.logit_scale_a.exp())          # how "sharp" CLAP's matching is

        per_window = [labels[i] for i in (audio @ text.T).argmax(axis=1)]
        overall = audio.mean(axis=0)
        overall /= np.linalg.norm(overall)
        logits = scale * (text @ overall)
        probs = np.exp(logits - logits.max())
        probs /= probs.sum()
        top = probs.argsort()[::-1][:3]
        return per_window, [{"label": labels[i], "score": round(float(probs[i]), 3)} for i in top]


# Descriptions the background music is compared with (Part 1, "what the music sounds like").
# The last one catches tracks that are mostly leftover speech or have no real music.
MUSIC_LABELS = [
    "calm ambient music",
    "soft piano music",
    "tense dramatic cinematic music",
    "epic orchestral music",
    "mysterious suspenseful music",
    "upbeat energetic electronic music",
    "happy cheerful music",
    "sad melancholic music",
    "a person talking with no music",
]


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

    def analyze(self, segments_audio: list[dict], video_id: str = ""):
        """Same as RealEmotionModel.analyze(): the mock has no embeddings."""
        return self.predict(segments_audio, video_id), None

    def describe(self, embeddings, labels=None):
        """The mock can't describe music: no labels at all."""
        return [], []


class RealEmotionModel:
    """
    The real pipeline: audio windows -> CLAP embeddings (frozen, pretrained)
    -> my trained BiLSTM+attention head -> valence/arousal per window.
    """

    def __init__(self, weights_path):
        import torch

        from backend.emotion_head import EmotionHead

        self.torch = torch
        checkpoint = torch.load(weights_path, map_location="cpu")  # the file saved by notebook 02
        self.head = EmotionHead(**checkpoint["config"])            # rebuild the same network...
        self.head.load_state_dict(checkpoint["state_dict"])        # ...and fill in the trained weights
        self.head.eval()                                           # inference mode: dropout switched off
        self.embedder = ClapEmbedder()
        # Warm-up: PyTorch is ~3x slower on its very first run, so do that run now (at start-up)
        # instead of during the first analysis.
        self.embedder.embed([{"audio": np.zeros(10 * SAMPLE_RATE, dtype=np.float32)}])
        self.info = {
            "embedding_model": "clap-htsat-unfused",
            "head": checkpoint.get("head_name", "bilstm_attention_v1"),
            "mock": False,
        }

    def predict(self, segments_audio: list[dict], video_id: str = "") -> list[dict]:
        """Same interface as MockEmotionModel. video_id is not needed here and is ignored."""
        return self.analyze(segments_audio)[0]

    def describe(self, embeddings, labels=MUSIC_LABELS):
        """What the audio sounds like in words (see ClapEmbedder.describe)."""
        return self.embedder.describe(embeddings, labels)

    def analyze(self, segments_audio: list[dict], video_id: str = ""):
        """Like predict(), but also returns the CLAP embeddings so they can be reused (e.g. describe())."""
        embeddings = self.embedder.embed(segments_audio)              # (windows, 512)
        x = self.torch.tensor(embeddings).unsqueeze(0)                # (1, windows, 512): a batch of one video
        mask = self.torch.ones(1, len(embeddings), dtype=self.torch.bool)  # every window is real (no padding)
        with self.torch.no_grad():
            output = self.head(x, mask)[0].numpy()                    # (windows, 2)

        predictions = [
            {
                "start_s": seg["start_s"],
                "end_s": seg["end_s"],
                "valence": round(float(v), 3),
                "arousal": round(float(a), 3),
            }
            for seg, (v, a) in zip(segments_audio, output)
        ]
        return predictions, embeddings


def get_model(use_mock: bool, weights_path=None):
    """Pick the model based on the USE_MOCK_MODEL setting."""
    if use_mock:
        return MockEmotionModel()
    if weights_path is None or not Path(weights_path).exists():
        raise FileNotFoundError(
            f"Trained weights not found at '{weights_path}'. Download c4_emotion_head.pt from "
            "Google Drive (C4/training/) into the models/ folder, or set USE_MOCK_MODEL=true."
        )
    return RealEmotionModel(weights_path)


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
