"""A tiny numpy machine-learning toolkit shared by the three cleaning models (no machine-learning library needed)."""

import math
import random
import re
from collections import Counter
from functools import lru_cache

import numpy as np

_WORD = re.compile(r"[a-z0-9']+")


def words_of(text: str) -> list[str]:
    """Lower-case words only: punctuation and capitalisation are ignored."""
    return _WORD.findall(text.lower())


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_logistic_irls(X: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 30):
    """Ridge-regularised logistic regression by Newton's method (for a few dense features). Returns (mean, std, w, b)."""
    mean, std = X.mean(axis=0), X.std(axis=0)
    std[std < 1e-9] = 1.0
    Z = np.hstack([np.ones((len(X), 1)), (X - mean) / std])
    w = np.zeros(Z.shape[1])
    reg = np.full(Z.shape[1], l2)
    reg[0] = 0.0
    for _ in range(iters):
        p = sigmoid(Z @ w)
        s = p * (1 - p) + 1e-6
        step = np.linalg.solve(Z.T @ (Z * s[:, None]) + np.diag(reg), Z.T @ (p - y) + reg * w)
        w -= step
        if np.abs(step).max() < 1e-6:
            break
    return mean, std, w[1:], float(w[0])


def _adam(params, grads, m, v, step, lr):
    for i, g in enumerate(grads):
        m[i] = 0.9 * m[i] + 0.1 * g
        v[i] = 0.999 * v[i] + 0.001 * g**2
        params[i] = params[i] - lr * (m[i] / (1 - 0.9**step)) / (np.sqrt(v[i] / (1 - 0.999**step)) + 1e-8)


def fit_logistic_dense(X: np.ndarray, y: np.ndarray, l2: float = 1e-3, iters: int = 120, lr: float = 0.2):
    """Class-balanced, L2-regularised logistic regression for many dense features, trained with Adam."""
    n, d = X.shape
    pos = float(y.sum())
    sw = np.where(y == 1, n / (2 * pos), n / (2 * (n - pos))).astype(np.float32)
    params, m, v = [np.zeros(d, dtype=np.float32), np.zeros(1)], [np.zeros(d), np.zeros(1)], [np.zeros(d), np.zeros(1)]
    for step in range(1, iters + 1):
        err = (sigmoid(X @ params[0] + params[1][0]) - y) * sw / n
        _adam(params, [X.T @ err + l2 * params[0], np.array([err.sum()])], m, v, step, lr)
    return params[0].astype(np.float32), float(params[1][0])


def fit_logistic_sparse(idx: np.ndarray, y: np.ndarray, dim: int, l2: float = 1e-4, iters: int = 150, lr: float = 0.3):
    """Logistic regression where every example switches on k of `dim` binary features (idx is n x k). Class-balanced."""
    n = len(y)
    pos = float(y.sum())
    sw = np.where(y == 1, n / (2 * pos), n / (2 * (n - pos))).astype(np.float32)
    params, m, v = [np.zeros(dim, dtype=np.float32), np.zeros(1)], [np.zeros(dim), np.zeros(1)], [np.zeros(dim), np.zeros(1)]
    for step in range(1, iters + 1):
        err = (sigmoid(params[0][idx].sum(axis=1) + params[1][0]) - y) * sw / n
        grad = np.zeros(dim, dtype=np.float32)
        np.add.at(grad, idx, err[:, None])
        _adam(params, [grad + l2 * params[0], np.array([err.sum()])], m, v, step, lr)
    return params[0].astype(np.float32), float(params[1][0])


def scores(truth: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    """How many real positives were found (recall), how often a negative was flagged by mistake, precision and F1."""
    tp, fp = int(((pred == 1) & (truth == 1)).sum()), int(((pred == 1) & (truth == 0)).sum())
    fn, tn = int(((pred == 0) & (truth == 1)).sum()), int(((pred == 0) & (truth == 0)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "caught": round(recall, 4),
        "wrongly_flagged": round(fp / (fp + tn), 4) if fp + tn else 0.0,
        "precision": round(precision, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
    }


def folds_of(n: int, k: int, rng: random.Random) -> list[list[int]]:
    """k random folds of range(n)."""
    idx = list(range(n))
    rng.shuffle(idx)
    return [idx[i::k] for i in range(k)]


# ---------------------------------------------------------------- TF-IDF sentence features
MAX_FEATURES = 6000
MIN_DOC_FREQ = 2


@lru_cache(maxsize=4096)  # the same sentences are re-used across every cross-check round
def sentence_features(text: str) -> Counter[str]:
    """Words, word pairs and letter groups (3-5 letters, so spelling variants still match) with their counts."""
    words = words_of(text)
    counts: Counter[str] = Counter(words)
    counts.update(f"{a} {b}" for a, b in zip(words, words[1:], strict=False))
    for word in words:
        padded = f" {word} "
        for n in (3, 4, 5):
            counts.update("#" + padded[i : i + n] for i in range(len(padded) - n + 1))
    return counts


class Vectorizer:
    """TF-IDF over the sentence features. It is fitted on training sentences only."""

    def __init__(self, vocabulary: list[str], idf: list[float]):
        self.vocabulary = vocabulary
        self.idf = np.asarray(idf, dtype=np.float32)
        self.index = {f: i for i, f in enumerate(vocabulary)}

    @classmethod
    def fit(cls, texts: list[str]) -> "Vectorizer":
        doc_freq: Counter[str] = Counter()
        for text in texts:
            doc_freq.update(sentence_features(text).keys())
        kept = [f for f, c in doc_freq.most_common() if c >= MIN_DOC_FREQ][:MAX_FEATURES]
        n = len(texts)
        return cls(kept, [math.log((1 + n) / (1 + doc_freq[f])) + 1 for f in kept])

    def transform(self, texts: list[str]) -> np.ndarray:
        X = np.zeros((len(texts), len(self.vocabulary)), dtype=np.float32)
        for row, text in enumerate(texts):
            for feature, count in sentence_features(text).items():
                j = self.index.get(feature)
                if j is not None:
                    X[row, j] = (1 + math.log(count)) * self.idf[j]
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        return X / np.where(norms == 0, 1, norms)
