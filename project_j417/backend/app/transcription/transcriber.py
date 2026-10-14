"""Speech recognition with faster-whisper (CTranslate2).

Accuracy + speed choices:
  * GPU: Whisper large-v3-turbo, float16 - near large-v3 accuracy, several times faster.
  * BatchedInferencePipeline - decodes many VAD-detected speech chunks in parallel
    (typically 3-4x faster than sequential decoding).
  * Silero VAD - skips silence/music, which is also the main source of hallucinated text.
  * beam_size 5 + Whisper's built-in temperature fallback for hard passages.
"""

import math
import os
import threading
from collections.abc import Callable
from pathlib import Path

from app.config import AsrConfig


class Transcriber:
    def __init__(self, cfg: AsrConfig):
        self.cfg = cfg
        self._pipeline = None
        self._load_lock = threading.Lock()

    def load(self) -> None:
        with self._load_lock:
            if self._pipeline is not None:
                return
            from faster_whisper import BatchedInferencePipeline, WhisperModel

            model = WhisperModel(
                self.cfg.model,
                device=self.cfg.device,
                compute_type=self.cfg.compute_type,
                cpu_threads=(os.cpu_count() or 4) if self.cfg.device == "cpu" else 0,
            )
            self._pipeline = BatchedInferencePipeline(model=model)

    def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
        word_timestamps: bool = False,
        on_progress: Callable[[float], None] | None = None,
    ) -> tuple[list[dict], dict]:
        self.load()
        segments_iter, info = self._pipeline.transcribe(
            str(audio_path),
            language=language or None,
            batch_size=self.cfg.batch_size,
            beam_size=self.cfg.beam_size,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            word_timestamps=word_timestamps,
            without_timestamps=False,  # sentence-level segments, not one blob per 30 s chunk
        )

        segments: list[dict] = []
        total = float(info.duration or 0) or None
        for seg in segments_iter:
            text = seg.text.strip()
            if not text:
                continue
            item: dict = {
                "id": len(segments),
                "start": round(float(seg.start), 2),
                "end": round(float(seg.end), 2),
                "text": text,
                "confidence": _confidence(getattr(seg, "avg_logprob", None)),
            }
            if word_timestamps and getattr(seg, "words", None):
                item["words"] = [
                    {
                        "start": round(float(w.start), 2),
                        "end": round(float(w.end), 2),
                        "word": w.word.strip(),
                        "probability": round(float(w.probability), 3),
                    }
                    for w in seg.words
                ]
            segments.append(item)
            if on_progress and total:
                on_progress(min(float(seg.end) / total, 1.0))

        meta = {
            "language": info.language,
            "language_probability": round(float(info.language_probability), 3),
            "duration": float(info.duration or 0),
        }
        return segments, meta


def _confidence(avg_logprob: float | None) -> float | None:
    if avg_logprob is None:
        return None
    return round(max(0.0, min(1.0, math.exp(avg_logprob))), 3)
