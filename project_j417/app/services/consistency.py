from app.core.config import CONSISTENCY_MODEL, CONSISTENCY_THRESHOLD
from app.services.embedding import embed_texts


def check_consistency(pairs: list[tuple[str, str]], threshold: float = CONSISTENCY_THRESHOLD) -> dict:
    if not pairs:
        return {"mean_score": None, "min_score": None, "threshold": threshold, "flagged": []}
    src = embed_texts([p[0] for p in pairs], model_name=CONSISTENCY_MODEL)
    tgt = embed_texts([p[1] for p in pairs], model_name=CONSISTENCY_MODEL)
    scores = (src * tgt).sum(axis=1)          # vectors are normalized, so this is cosine
    flagged = [
        {"source": s, "translation": t, "score": round(float(sc), 3)}
        for (s, t), sc in zip(pairs, scores) if sc < threshold
    ]
    return {
        "mean_score": round(float(scores.mean()), 3),
        "min_score": round(float(scores.min()), 3),
        "threshold": threshold,
        "flagged": flagged,
    }