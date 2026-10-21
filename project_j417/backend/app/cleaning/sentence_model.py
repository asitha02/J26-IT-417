"""Model 1: which whole SENTENCES are redundant (subscribe requests, sponsor reads, thank-you endings...).

TF-IDF features of words (single words and pairs) and letter groups -> logistic regression, in plain numpy.
Tested on sentences it was not trained on (5-fold), on a whole kind of sentence hidden from training
(leave-one-kind-out), and against the hand-written word list on the same sentences. It replaces the word
list only if it is at least as good and rarely removes real content.
"""

import random
from datetime import datetime, timezone

import numpy as np

from app.cleaning import rules
from app.cleaning.data import FAMILIES, TRICKY_CONTENT
from app.cleaning.ml import Vectorizer, fit_logistic_dense, folds_of, scores, sigmoid

THRESHOLD = 0.5
MAX_FALSE_ALARM = 0.02   # the model must wrongly drop at most 2% of real content to be used
MIN_REAL_SENTENCES = 100
MAX_REAL_SENTENCES = 800


class SentenceModel:
    def __init__(self, vectorizer: Vectorizer, weights: np.ndarray, bias: float, threshold: float = THRESHOLD):
        self.vectorizer, self.weights, self.bias, self.threshold = vectorizer, weights, bias, threshold

    @classmethod
    def fit(cls, texts: list[str], labels: np.ndarray) -> "SentenceModel":
        vectorizer = Vectorizer.fit(texts)
        weights, bias = fit_logistic_dense(vectorizer.transform(texts), labels.astype(np.float32))
        return cls(vectorizer, weights, bias)

    def probability(self, sentences: list[str]) -> np.ndarray:
        return sigmoid(self.vectorizer.transform(sentences) @ self.weights + self.bias)

    def is_redundant(self, sentence: str) -> bool:
        return bool(self.probability([sentence])[0] >= self.threshold)

    def to_json(self) -> dict:
        return {"vocabulary": self.vectorizer.vocabulary, "idf": [round(float(v), 5) for v in self.vectorizer.idf],
                "weights": [round(float(v), 5) for v in self.weights], "bias": self.bias, "threshold": self.threshold}

    @classmethod
    def from_json(cls, d: dict) -> "SentenceModel":
        return cls(Vectorizer(d["vocabulary"], d["idf"]), np.asarray(d["weights"], dtype=np.float32), d["bias"], d["threshold"])


class TrainingError(ValueError):
    pass


def train(real: list[str], seed: int = 0) -> tuple[SentenceModel, dict]:
    if len(real) < MIN_REAL_SENTENCES:
        raise TrainingError(
            f"Not enough real text to train on: need {MIN_REAL_SENTENCES}+ clear sentences from your videos, "
            f"have {len(real)}. Add more videos first."
        )
    rng = random.Random(seed)
    real = list(real)
    rng.shuffle(real)
    real = real[:MAX_REAL_SENTENCES]

    texts, labels, kind = [], [], []
    for name, sentences in FAMILIES.items():
        texts += sentences
        labels += [1] * len(sentences)
        kind += [name] * len(sentences)
    for s in TRICKY_CONTENT + real:
        texts.append(s)
        labels.append(0)
        kind.append("")
    y, k, X = np.array(labels), np.array(kind), np.array(texts, dtype=object)

    # 1. new sentences of known kinds: 5-fold cross-check (the folds keep the same share of each class)
    pos = [i for i in range(len(y)) if y[i] == 1]
    neg = [i for i in range(len(y)) if y[i] == 0]
    folds = [sorted([pos[i] for i in a] + [neg[j] for j in b]) for a, b in
             zip(folds_of(len(pos), 5, rng), folds_of(len(neg), 5, rng), strict=True)]
    pred = np.zeros(len(y), dtype=int)
    for held in folds:
        train_idx = [i for f in folds if f is not held for i in f]
        m = SentenceModel.fit(list(X[train_idx]), y[train_idx])
        pred[held] = m.probability(list(X[held])) >= THRESHOLD
    unseen_sentences = scores(y, pred)

    # 2. a kind never seen: hide one whole kind from training and see how much of it is still caught
    rng.shuffle(neg)
    cut = int(len(neg) * 0.8)
    neg_train, neg_test = np.array(neg[:cut]), np.array(neg[cut:])
    per_kind, fpr = [], []
    for name in FAMILIES:
        held = np.flatnonzero(k == name)
        train_idx = np.concatenate([np.flatnonzero((y == 1) & (k != name)), neg_train])
        m = SentenceModel.fit(list(X[train_idx]), y[train_idx])
        per_kind.append({"kind": name, "caught": round(float((m.probability(list(X[held])) >= THRESHOLD).mean()), 4),
                         "sentences": int(len(held))})
        fpr.append(float((m.probability(list(X[neg_test])) >= THRESHOLD).mean()))
    never_seen = {"caught": round(float(np.mean([p["caught"] for p in per_kind])), 4),
                  "wrongly_flagged": round(float(np.mean(fpr)), 4), "per_kind": per_kind}

    # 3. the hand-written word list on the very same sentences
    rule_scores = scores(y, np.array([int(rules.is_boilerplate(t)) for t in texts]))

    model = SentenceModel.fit(texts, y)
    flagged = [s for s, p in zip(real, model.probability(real), strict=True) if p >= THRESHOLD]
    activated = unseen_sentences["f1"] >= rule_scores["f1"] and unseen_sentences["wrongly_flagged"] <= MAX_FALSE_ALARM
    report = {
        "examples": {"redundant": int((y == 1).sum()), "kinds": list(FAMILIES), "real_sentences": len(real),
                     "tricky_content": len(TRICKY_CONTENT)},
        "model": unseen_sentences,
        "never_seen_kind": never_seen,
        "rules": rule_scores,
        "activated": bool(activated),
        "on_your_videos": {"sentences_checked": len(real), "flagged": len(flagged), "examples": flagged[:8]},
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return model, report
