"""Model 2: which WORDS are errors - filler words ("um", "you know") and stuttered repeats ("the the").

A word tagger: for every word of a sentence it decides "keep" or "remove" from the word itself and the words
around it (previous word, next word, commas, whether it repeats the word before). The features are hashed into
a fixed table and a logistic regression is trained on them in plain numpy.

Training data is made automatically: real sentences that need no cleaning get mistakes ADDED on purpose, so
the right answer for every word is known. It is tested on sentences it was not trained on (5-fold):
  * restored exactly : after cleaning, the sentence has exactly its original words again
  * false edits      : how often it changes a clean sentence it should have left alone
and compared with the hand-written regex rules on the same noisy sentences. It replaces the rules only if it
restores at least as many sentences and rarely edits clean ones.
"""

import random
import re
import zlib
from datetime import datetime, timezone

import numpy as np

from app.cleaning import rules
from app.cleaning.ml import fit_logistic_sparse, folds_of, sigmoid, words_of

TOKEN = re.compile(r"[A-Za-z0-9']+|[^\sA-Za-z0-9']")
DIM = 1 << 15
SLOTS = 12
THRESHOLD = 0.5
MAX_FALSE_EDIT_RATE = 0.02
MIN_SENTENCES = 40
VARIANTS_TRAIN = 6
VARIANTS_TEST = 3

SINGLE_FILLERS = ["um", "umm", "uh", "uhh", "uhm", "er", "erm", "ah", "hmm", "mm"]
PHRASE_FILLERS = [["you", "know"], ["i", "mean"], ["you", "see"], ["basically"], ["literally"], ["honestly"],
                  ["okay", "so"], ["so", "yeah"]]


def tokenize(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(text)]


def _is_word(tok: str) -> bool:
    return tok[0].isalnum() or tok[0] == "'"


def _h(s: str) -> int:
    return zlib.crc32(s.encode()) % DIM


def features(tokens: list[str], i: int) -> list[int]:
    """The 12 features (as hashed ids) of the word at position i."""
    low = [t.lower() for t in tokens]
    w = low[i]
    p1, p2, p3 = (low[i - 1] if i >= 1 else "<s>"), (low[i - 2] if i >= 2 else "<s>"), (low[i - 3] if i >= 3 else "<s>")
    n1 = low[i + 1] if i + 1 < len(low) else "</s>"
    prev_comma, next_comma = p1 == ",", n1 == ","
    return [
        _h("w=" + w), _h("p1=" + p1), _h("n1=" + n1), _h(f"p1w={p1}|{w}"), _h(f"wn1={w}|{n1}"),
        _h(f"same_prev={w == p1}|{w if w == p1 else ''}"), _h(f"rep2={w == p2 and (n1 == p1 or p1 == p3)}"),  # a two-word stutter repeats BOTH words: a b a b
        _h(f"pc={prev_comma}|{w}"), _h(f"nc={next_comma}|{w}"),
        _h(f"first={i == 0}|{w}"), _h(f"last={i == len(low) - 1}|{w}"), _h("bias"),
    ]


def inject(text: str, rng: random.Random) -> tuple[list[str], list[int]]:
    """The sentence's tokens with 1-3 mistakes added, and for each token 1 if it is an added error word."""
    tokens = [t for t, _, _ in tokenize(text)]
    labels = [0] * len(tokens)
    for _ in range(rng.randint(1, 3)):
        word_positions = [i for i, t in enumerate(tokens) if _is_word(t)]
        if rng.random() < 0.65:  # a filler
            filler = rng.choice(SINGLE_FILLERS) if rng.random() < 0.6 else " ".join(rng.choice(PHRASE_FILLERS))
            parts = filler.split()
            pos = rng.choice(word_positions + [len(tokens)] if len(word_positions) else [0])
            pos = min(pos, len(tokens))
            commas = rng.random() < 0.6
            new = ([","] if commas and pos > 0 else []) + parts + ([","] if commas else [])
            lab = [0] if commas and pos > 0 else []
            lab = lab + [1] * len(parts) + ([0] if commas else [])
            tokens[pos:pos] = new
            labels[pos:pos] = lab
        else:  # a stutter: the previous word (or two words) said twice
            idx = rng.choice(word_positions)
            span = 2 if rng.random() < 0.3 and idx + 1 < len(tokens) and _is_word(tokens[idx + 1]) else 1
            copy = tokens[idx : idx + span]
            tokens[idx + span : idx + span] = copy
            labels[idx + span : idx + span] = [1] * span
    return tokens, labels


def _render(tokens: list[str]) -> str:
    text = " ".join(tokens)
    return re.sub(r"\s+([,.!?;:])", r"\1", text)


def _dataset(sentences: list[str], variants: int, seed: int, include_clean: bool = False):
    """Token rows for `variants` noisy copies of every sentence. With include_clean, the untouched sentence is also
    added as an example of "leave all of this alone" (so the model sees plain real speech, not only damaged speech)."""
    rng = random.Random(seed)
    idx_rows, labels, noisy = [], [], []
    for s in sentences:
        versions = [(s, [t for t, _, _ in tokenize(s)], None)] if include_clean else []
        versions += [(s, *inject(s, rng)) for _ in range(variants)]
        for _, tokens, lab in versions:
            lab = lab if lab is not None else [0] * len(tokens)
            noisy.append((s, tokens, lab))
            for i, t in enumerate(tokens):
                if _is_word(t):
                    idx_rows.append(features(tokens, i))
                    labels.append(lab[i])
    return np.array(idx_rows, dtype=np.int64), np.array(labels, dtype=np.float32), noisy


class WordModel:
    def __init__(self, weights: np.ndarray, bias: float, threshold: float = THRESHOLD):
        self.weights, self.bias, self.threshold = weights, bias, threshold

    @classmethod
    def fit(cls, sentences: list[str], seed: int = 0) -> "WordModel":
        idx, y, _ = _dataset(sentences, VARIANTS_TRAIN, seed, include_clean=True)
        w, b = fit_logistic_sparse(idx, y, DIM)
        return cls(w, b)

    def _flags(self, tokens: list[str]) -> list[bool]:
        pos = [i for i, t in enumerate(tokens) if _is_word(t)]
        if not pos:
            return [False] * len(tokens)
        idx = np.array([features(tokens, i) for i in pos])
        probs = sigmoid(self.weights[idx].sum(axis=1) + self.bias)
        out = [False] * len(tokens)
        for i, p in zip(pos, probs, strict=True):
            out[i] = bool(p >= self.threshold)
        return out

    def apply(self, text: str) -> str:
        """The text with its error words removed (unchanged if there are none)."""
        spans = tokenize(text)
        flags = self._flags([t for t, _, _ in spans])
        if not any(flags):
            return text
        out, last = [], 0
        for (_, start, end), bad in zip(spans, flags, strict=True):
            if bad:
                out.append(text[last:start])
                last = end
        out.append(text[last:])
        s = "".join(out)
        s = re.sub(r"\s+([,.!?;:])", r"\1", s)
        s = re.sub(r",(\s*,)+", ",", s)
        s = re.sub(r"^[\s,]+", "", s)
        return re.sub(r"\s+", " ", s).strip()

    def to_json(self) -> dict:
        nz = np.flatnonzero(self.weights)
        return {"dim": DIM, "index": nz.tolist(), "weights": [round(float(self.weights[i]), 5) for i in nz],
                "bias": self.bias, "threshold": self.threshold}

    @classmethod
    def from_json(cls, d: dict) -> "WordModel":
        w = np.zeros(d["dim"], dtype=np.float32)
        w[np.asarray(d["index"], dtype=np.int64)] = d["weights"]
        return cls(w, d["bias"], d["threshold"])


class TrainingError(ValueError):
    pass


THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]


def _evaluate(rounds: list, threshold: float) -> dict:
    """Score the held-out sentences of every cross-check round at one 'how sure must it be' threshold."""
    tp = fp = fn = restored = total = edited = clean_total = 0
    for model, noisy, clean in rounds:
        model.threshold = threshold
        for original, tokens, lab in noisy:
            flags = model._flags(tokens)
            for i, t in enumerate(tokens):
                if _is_word(t):
                    tp += flags[i] and lab[i] == 1
                    fp += flags[i] and lab[i] == 0
                    fn += (not flags[i]) and lab[i] == 1
            total += 1
            restored += words_of(model.apply(_render(tokens))) == words_of(original)
        for s in clean:  # clean sentences must come out untouched
            clean_total += 1
            edited += words_of(model.apply(s)) != words_of(s)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"threshold": threshold, "restored_exactly": round(restored / total, 4),
            "false_edit_rate": round(edited / clean_total, 4),
            "error_words_caught": round(recall, 4), "error_words_precision": round(precision, 4)}


def train(base: list[str], seed: int = 0) -> tuple[WordModel, dict]:
    if len(base) < MIN_SENTENCES:
        raise TrainingError(
            f"Not enough clean sentences to build the word test: need {MIN_SENTENCES}+, have {len(base)}. Add more videos first."
        )
    rng = random.Random(seed)
    base = list(base)
    rng.shuffle(base)
    folds = folds_of(len(base), 5, rng)

    rounds, rule_restored, rule_edited, total, clean_total = [], 0, 0, 0, 0
    for held in folds:  # 5-fold: every sentence is tested by a model that never saw it
        test = [base[i] for i in held]
        model = WordModel.fit([base[i] for f in folds if f is not held for i in f], seed)
        _, _, noisy = _dataset(test, VARIANTS_TEST, seed + 1)
        rounds.append((model, noisy, test))
        for original, tokens, _ in noisy:
            total += 1
            rule_restored += words_of(rules.clean_words(_render(tokens))) == words_of(original)
        for s in test:
            clean_total += 1
            rule_edited += words_of(rules.clean_words(s)) != words_of(s)

    # How sure must the model be before it removes a word? The most cautious setting is not always needed:
    # take the lowest threshold that still edits at most 2% of clean sentences (chosen on the cross-check).
    grid = [_evaluate(rounds, t) for t in THRESHOLDS]
    allowed = [g for g in grid if g["false_edit_rate"] <= MAX_FALSE_EDIT_RATE]
    best = max(allowed, key=lambda g: (g["restored_exactly"], -g["threshold"])) if allowed else min(grid, key=lambda g: g["false_edit_rate"])
    final = WordModel.fit(base, seed)
    final.threshold = best["threshold"]

    rule_stats = {"restored_exactly": round(rule_restored / total, 4), "false_edit_rate": round(rule_edited / clean_total, 4)}
    activated = best["restored_exactly"] >= rule_stats["restored_exactly"] and best["false_edit_rate"] <= MAX_FALSE_EDIT_RATE
    report = {
        "examples": {"clean_sentences": len(base), "noisy_versions": len(base) * VARIANTS_TRAIN,
                     "filler_kinds": len(SINGLE_FILLERS) + len(PHRASE_FILLERS)},
        "model": {k: v for k, v in best.items()},
        "rules": rule_stats,
        "thresholds_tried": grid,
        "test_sentences": total,
        "activated": bool(activated),
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return final, report