"""
Separates the narration (speech) from the background (music + sound effects) with Demucs.

Why: the research question is about the BACKGROUND audio. My emotion model was trained on
DEAM, which is music, so giving it the music-only track also brings the input closer to the
training data. The speech track is used to measure whether the music is too loud under it.

Demucs (htdemucs, Meta) is pretrained and used frozen. It splits audio into 4 tracks:
drums, bass, other and vocals. Here: speech = vocals; background = drums + bass + other.
"""
import logging

import librosa
import numpy as np

from backend.config import SAMPLE_RATE

logger = logging.getLogger("c4.separation")

DEMUCS_MODEL_NAME = "htdemucs"


def combine_sources(sources: dict) -> tuple[np.ndarray, np.ndarray]:
    """
    sources: {"drums": array, "bass": array, "other": array, "vocals": array} (mono, same length)
    Returns (speech, background): vocals vs. everything else added together.
    """
    speech = sources["vocals"]
    background = sum(audio for name, audio in sources.items() if name != "vocals")
    return speech, background


class Separator:
    """Loads Demucs once (about 35 s) and reuses it for every request."""

    def __init__(self):
        # Imported here so the backend still starts if separation is switched off.
        import torch
        from demucs.apply import apply_model
        from demucs.pretrained import get_model

        self.torch = torch
        self.apply_model = apply_model
        self.model = get_model(DEMUCS_MODEL_NAME)
        self.model.eval()                                   # inference only, weights never change
        self.info = {"method": DEMUCS_MODEL_NAME}

    def separate(self, audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        audio: mono, SAMPLE_RATE (48 kHz).
        Returns (speech, background), both mono, 48 kHz, same length as the input.
        """
        sr = self.model.samplerate                          # Demucs works at 44.1 kHz, stereo
        x = librosa.resample(audio, orig_sr=SAMPLE_RATE, target_sr=sr)
        wav = self.torch.tensor(np.stack([x, x]))[None]     # (batch 1, 2 channels, samples)
        with self.torch.no_grad():
            out = self.apply_model(self.model, wav, device="cpu", progress=False, split=True, overlap=0.1)[0]

        # out: (4 sources, 2 channels, samples) -> mono per source, back to 48 kHz, same length as input
        sources = {}
        for i, name in enumerate(self.model.sources):
            mono = out[i].mean(0).numpy()
            mono = librosa.resample(mono, orig_sr=sr, target_sr=SAMPLE_RATE)
            sources[name] = _match_length(mono, len(audio))
        return combine_sources(sources)


class NoSeparation:
    """Used when USE_SOURCE_SEPARATION=false: the 'background' is simply the mixed audio."""

    info = {"method": "none"}

    def separate(self, audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return np.zeros_like(audio), audio


def get_separator(enabled: bool):
    return Separator() if enabled else NoSeparation()


def _match_length(audio: np.ndarray, length: int) -> np.ndarray:
    """Cut or pad with silence so all tracks line up sample by sample with the original."""
    if len(audio) >= length:
        return audio[:length]
    return np.pad(audio, (0, length - len(audio)))
