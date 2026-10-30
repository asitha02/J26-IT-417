"""Model 3: are two sentences DUPLICATES (the same content said twice, even with a few words different)?

Five similarity signals of a pair of sentences (word overlap, containment, order-aware match, length ratio,
shared word triples) go into a logistic regression, trained in numpy. It learns how to weigh them instead of
using one fixed overlap threshold.

Training pairs are made automatically from real sentences:
  * duplicates    : a sentence and a noisy copy of it (words dropped or changed, a filler added, two words swapped)
  * not duplicates: a sentence and a different one (random ones, the most similar other sentence, and an invented
                    look-alike with 30-55% of its words changed)
Tested on sentences it was not trained on (5-fold) against the best fixed overlap threshold (chosen on the
training folds only). It replaces the threshold only if it is at least as good and rarely merges different sentences.
"""

import difflib
import random
from datetime import datetime, timezone

import numpy as np

from app.cleaning import rules
from app.cleaning.ml import fit_logistic_irls, folds_of, scores, sigmoid, words_of

THRESHOLD = 0.5
MAX_FALSE_ALARM = 0.02
MIN_SENTENCES = 40
FEATURES = ["word overlap", "containment", "order-aware match", "length ratio", "shared word triples"]
FILLERS = ["um", "uh", "so", "you know", "like"]


def _triples(w: list[str]) -> set[tuple[str, ...]]:
    return {tuple(w[i : i + 3]) for i in range(len(w) - 2)}


def pair_features(a: list[str], b: list[str]) -> list[float]:
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    ta, tb = _triples(a), _triples(b)
    return [
        inter / max(len(sa | sb), 1),
        inter / max(min(len(sa), len(sb)), 1),
        difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(),
        min(len(a), len(b)) / max(len(a), len(b), 1),
        len(ta & tb) / max(min(len(ta), len(tb)), 1),
    ]


class DuplicateModel:
    def __init__(self, mean, std, weights, bias, threshold: float = THRESHOLD):
        self.mean, self.std, self.weights, self.bias, self.threshold = (
            np.asarray(mean), np.asarray(std), np.asarray(weights), bias, threshold)

    @classmethod
    def fit(cls, X: np.ndarray, y: np.ndarray) -> "DuplicateModel":
        mean, std, w, b = fit_logistic_irls(X, y)
        return cls(mean, std, w, b)

    def probability(self, X: np.ndarray) -> np.ndarray:
        return sigmoid(((X - self.mean) / self.std) @ self.weights + self.bias)

    def is_duplicate(self, a: list[str], b: list[str]) -> bool:
        return bool(self.probability(np.array([pair_features(a, b)]))[0] >= self.threshold)

    def to_json(self) -> dict:
        return {"mean": self.mean.tolist(), "std": self.std.tolist(), "weights": self.weights.tolist(),
                "bias": self.bias, "threshold": self.threshold}

    @classmethod
    def from_json(cls, d: dict) -> "DuplicateModel":
        return cls(d["mean"], d["std"], d["weights"], d["bias"], d["threshold"])


class TrainingError(ValueError):
    pass


def _noisy_copy(w: list[str], vocab: list[str], rng: random.Random) -> list[str]:
    out = list(w)
    for _ in range(rng.randint(0, 3)):
        kind = rng.random()
        if kind < 0.4 and len(out) > 5:
            out.pop(rng.randrange(len(out)))                              # a word missing
        elif kind < 0.7:
            out[rng.randrange(len(out))] = rng.choice(vocab)              # a word recognised differently
        elif kind < 0.85 and len(out) > 2:
            i = rng.randrange(len(out) - 1)
            out[i], out[i + 1] = out[i + 1], out[i]                       # two words swapped
        else:
            pos = rng.randrange(len(out) + 1)
            out[pos:pos] = rng.choice(FILLERS).split()                    # a filler added
    return out


def _lookalike(w: list[str], vocab: list[str], rng: random.Random) -> list[str]:
    out = list(w)
    for i in rng.sample(range(len(out)), max(1, round(len(out) * rng.uniform(0.30, 0.55)))):
        out[i] = rng.choice(vocab)
    return out


def _pairs(sentences: list[list[str]], vocab: list[str], seed: int):
    """(features, label) rows from the given sentences."""
    rng = random.Random(seed)
    rows, labels = [], []
    for i, w in enumerate(sentences):
        rows.append(pair_features(w, _noisy_copy(w, vocab, rng)))
        labels.append(1)
        others = [j for j in range(len(sentences)) if j != i]
        if others:
            rows.append(pair_features(w, sentences[rng.choice(others)]))
            labels.append(0)
            hardest = max(others, key=lambda j: len(set(w) & set(sentences[j])) / max(len(set(w) | set(sentences[j])), 1))
            rows.append(pair_features(w, sentences[hardest]))
            labels.append(0)
        rows.append(pair_features(w, _lookalike(w, vocab, rng)))
        labels.append(0)
    return np.array(rows), np.array(labels, dtype=np.float64)


def _best_threshold(X: np.ndarray, y: np.ndarray) -> float:
    """The best fixed word-overlap threshold on the given pairs (the hand-written rule, tuned as well as it can be)."""
    best_t, best_f1 = rules.DUPLICATE_SIMILARITY, -1.0
    for t in np.arange(0.5, 0.96, 0.05):
        f1 = scores(y.astype(int), (X[:, 0] >= t).astype(int))["f1"]
        if f1 > best_f1:
            best_t, best_f1 = float(t), f1
    return best_t


def train(base: list[str], seed: int = 0) -> tuple[DuplicateModel, dict]:
    if len(base) < MIN_SENTENCES:
        raise TrainingError(
            f"Not enough clean sentences to build the duplicate test: need {MIN_SENTENCES}+, have {len(base)}. Add more videos first."
        )
    rng = random.Random(seed)
    sents = [words_of(s) for s in base]
    vocab = sorted({w for s in sents for w in s})
    order = list(range(len(sents)))
    rng.shuffle(order)
    folds = [[order[i] for i in f] for f in folds_of(len(order), 5, rng)]

    truth, model_pred, rule_pred, thresholds = [], [], [], []
    for n, held in enumerate(folds):
        train_s = [sents[i] for f in folds if f is not held for i in f]
        test_s = [sents[i] for i in held]
        Xtr, ytr = _pairs(train_s, vocab, seed)
        Xte, yte = _pairs(test_s, vocab, seed + 100 + n)
        model = DuplicateModel.fit(Xtr, ytr)
        t = _best_threshold(Xtr, ytr)
        thresholds.append(t)
        truth += yte.astype(int).tolist()
        model_pred += (model.probability(Xte) >= THRESHOLD).astype(int).tolist()
        rule_pred += (Xte[:, 0] >= t).astype(int).tolist()

    X, y = _pairs(sents, vocab, seed)
    final = DuplicateModel.fit(X, y)
    m, r = scores(np.array(truth), np.array(model_pred)), scores(np.array(truth), np.array(rule_pred))
    activated = m["f1"] >= r["f1"] and m["wrongly_flagged"] <= MAX_FALSE_ALARM
    report = {
        "examples": {"clean_sentences": len(base), "pairs": int(len(y))},
        "model": m,
        "rules": {**r, "threshold": round(float(np.mean(thresholds)), 2)},
        "learned_weights": {f: round(float(v), 3) for f, v in zip(FEATURES, final.weights, strict=True)},
        "test_pairs": len(truth),
        "activated": bool(activated),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return final, report
