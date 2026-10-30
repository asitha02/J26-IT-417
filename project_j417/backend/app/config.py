from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def cuda_available() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


@dataclass(frozen=True)
class AsrConfig:
    model: str
    device: str
    compute_type: str
    batch_size: int
    beam_size: int


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "research_project"

    data_dir: Path = Path("data")

    whisper_model: str = "auto"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    batch_size: int = 0
    beam_size: int = 0  # 0 = auto (5 on GPU, 1 on CPU)

    max_duration_sec: int = 4 * 3600
    max_concurrent_jobs: int = 1
    preload_model: bool = True
    keep_audio: bool = False
    ytdlp_cookies_file: str | None = None

    cors_origins: str = "http://localhost:5173"

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def transcript_dir(self) -> Path:
        return self.data_dir / "transcripts"

    def asr(self) -> AsrConfig:
        """Resolve 'auto' values: best accuracy+speed for the hardware present."""
        device = self.whisper_device
        if device == "auto":
            device = "cuda" if cuda_available() else "cpu"
        on_gpu = device == "cuda"

        model = self.whisper_model
        if model == "auto":
            # large-v3-turbo: near large-v3 accuracy at several times the speed.
            # CPU: English-only distilled small - ~2x faster than `small`, near-equal English accuracy.
            model = "large-v3-turbo" if on_gpu else "distil-small.en"

        compute = self.whisper_compute_type
        if compute == "auto":
            compute = "float16" if on_gpu else "int8"

        batch = self.batch_size or (16 if on_gpu else 8)
        beam = self.beam_size or (5 if on_gpu else 1)  # greedy decoding is much cheaper on CPU
        return AsrConfig(model, device, compute, batch, beam)


@lru_cache
def get_settings() -> Settings:
    return Settings()
