from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    return get_model().encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,   # dot product == cosine similarity
        show_progress_bar=False,
        convert_to_numpy=True,
    )


def similarity_matrix(embeddings: np.ndarray) -> np.ndarray:
    return embeddings @ embeddings.T