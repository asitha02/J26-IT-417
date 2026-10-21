"""Learned relevance ranker: a small L2-regularised logistic regression over clip features.

Why logistic regression: the label sets a person can produce by hand are small (tens to hundreds of
clips), where a handful of well-chosen features + a linear model generalises better than a deep
model, trains in milliseconds, needs only numpy, and its weights are directly interpretable
(which signal matters: keyword match, semantic match, ASR confidence, ...).

Training data = (features, 0/1 label, query-group). Evaluation is leave-one-query-out: every query
is held out once, the model is fitted on the rest, and the held-out clips are ranked. Reported
nDCG@10 / precision@5 are compared with the un-learned baselines on exactly the same clips.
"""

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# Order matters: stored with the model so old models keep working if features are added later.
FEATURES = [
    "lexical",     # BM25, min-max normalised within the query's candidates
    "semantic",    # embedding cosine, min-max normalised
    "bm25_log",    # log(1 + raw BM25): absolute strength of the keyword match
    "cosine",      # raw embedding cosine: absolute semantic similarity
    "coverage",    # share of the query's distinct words that appear in the clip
    "density",     # content words per second (talk vs. silence / filler)
    "confidence",  # ASR confidence
    "position",    # where in the video the clip starts (intros/outros are rarely useful)
    "length",      # clip length relative to a minute
]

MIN_LABELS, MIN_POSITIVES, MIN_NEGATIVES, MIN_QUERIES = 20, 5, 5, 3


class TrainingError(ValueError):
    pass


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


@dataclass
class LearnedRanker:
    features: list[str]
    mean: list[float]
    std: list[float]
    weights: list[float]
    bias: float
    trained_at: str = ""
    report: dict = field(default_factory=dict)

    def score(self, X: np.ndarray) -> np.ndarray:
        z = (X - np.asarray(self.mean)) / np.asarray(self.std)
        return _sigmoid(z @ np.asarray(self.weights) + self.bias)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "LearnedRanker":
        return cls(**json.loads(path.read_text(encoding="utf-8")))


def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 30):
    """Ridge-regularised logistic regression by IRLS (Newton). Returns (mean, std, w, bias)."""
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std < 1e-9] = 1.0
    Z = np.hstack([np.ones((len(X), 1)), (X - mean) / std])  # column 0 = bias (not penalised)
    w = np.zeros(Z.shape[1])
    reg = np.full(Z.shape[1], l2)
    reg[0] = 0.0
    for _ in range(iters):
        p = _sigmoid(Z @ w)
        s = p * (1 - p) + 1e-6
        grad = Z.T @ (p - y) + reg * w
        hess = Z.T @ (Z * s[:, None]) + np.diag(reg)
        step = np.linalg.solve(hess, grad)
        w -= step
        if np.abs(step).max() < 1e-6:
            break
    return mean, std, w[1:], float(w[0])


def ndcg_at_k(labels_in_rank_order: list[float], k: int = 10) -> float | None:
    """Binary-gain nDCG@k; None when the list has no relevant item (undefined)."""
    ideal = sorted(labels_in_rank_order, reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal[:k]))
    if idcg == 0:
        return None
    return sum(g / math.log2(i + 2) for i, g in enumerate(labels_in_rank_order[:k])) / idcg


def precision_at_k(labels_in_rank_order: list[float], k: int = 5) -> float:
    top = labels_in_rank_order[:k]
    return sum(top) / len(top) if top else 0.0


def _rank_metrics(scores: np.ndarray, y: np.ndarray) -> tuple[float | None, float]:
    order = np.argsort(-scores, kind="stable")
    ranked = y[order].tolist()
    return ndcg_at_k(ranked, 10), precision_at_k(ranked, 5)


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def train(samples: list[dict], l2: float = 1.0) -> LearnedRanker:
    """samples: [{"features": {name: value}, "label": 0|1, "group": str}, ...]"""
    rows = [s for s in samples if all(f in s["features"] for f in FEATURES)]
    X = np.array([[s["features"][f] for f in FEATURES] for s in rows], dtype=float)
    y = np.array([float(s["label"]) for s in rows])
    groups = np.array([s["group"] for s in rows])
    n_pos, n_neg, n_groups = int(y.sum()), int((1 - y).sum()), len(set(groups.tolist()))
    if len(rows) < MIN_LABELS or n_pos < MIN_POSITIVES or n_neg < MIN_NEGATIVES or n_groups < MIN_QUERIES:
        raise TrainingError(
            f"Need at least {MIN_LABELS} labels ({MIN_POSITIVES}+ relevant, {MIN_NEGATIVES}+ not relevant) "
            f"over {MIN_QUERIES}+ different queries; have {len(rows)} labels "
            f"({n_pos} relevant, {n_neg} not) over {n_groups} queries."
        )

    col = {f: i for i, f in enumerate(FEATURES)}
    baselines = {
        "bm25": lambda A: A[:, col["lexical"]],
        "semantic": lambda A: A[:, col["semantic"]],
        "fixed_hybrid": lambda A: 0.35 * A[:, col["lexical"]] + 0.65 * A[:, col["semantic"]],
    }
    names = [*baselines, "learned"]
    ndcg: dict[str, list[float]] = {n: [] for n in names}
    prec: dict[str, list[float]] = {n: [] for n in names}
    for g in sorted(set(groups.tolist())):  # leave-one-query-out
        test, train_ = groups == g, groups != g
        if y[test].sum() == 0 or y[train_].sum() == 0 or (1 - y[train_]).sum() == 0:
            continue
        mean, std, w, b = fit_logistic(X[train_], y[train_], l2)
        held = LearnedRanker(FEATURES, mean.tolist(), std.tolist(), w.tolist(), b)
        scorers = {**{n: f(X[test]) for n, f in baselines.items()}, "learned": held.score(X[test])}
        for n in names:
            nd, pr = _rank_metrics(scorers[n], y[test])
            if nd is not None:
                ndcg[n].append(nd)
                prec[n].append(pr)

    mean, std, w, b = fit_logistic(X, y, l2)  # final model uses every label
    return LearnedRanker(
        FEATURES,
        mean.tolist(),
        std.tolist(),
        w.tolist(),
        b,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
        {
            "n_labels": len(rows),
            "n_queries": n_groups,
            "positives": n_pos,
            "negatives": n_neg,
            "evaluated_queries": len(ndcg["learned"]),
            "metrics": {n: {"ndcg@10": _mean(ndcg[n]), "p@5": _mean(prec[n])} for n in names},
            "weights": {f: round(float(v), 4) for f, v in zip(FEATURES, w)},
        },
    )
