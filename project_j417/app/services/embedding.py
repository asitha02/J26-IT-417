from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import EMBEDDING_MODEL


@lru_cache(maxsize=4)
def get_model(name: str) -> SentenceTransformer:
    return SentenceTransformer(name)


def embed_texts(texts: list[str], batch_size: int = 32, model_name: str | None = None) -> np.ndarray:
    model = get_model(model_name or EMBEDDING_MODEL)
    return model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )


def similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    return embeddings @ embeddings.T