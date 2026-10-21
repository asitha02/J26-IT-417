"""Relevance ranking of video segments for a topic / audience.

Pipeline (all CPU, no GPU needed):
  1. Cleaning    - fillers, stutters and "like & subscribe" boilerplate removed (see clean.py).
  2. Windowing   - consecutive ASR segments merged into ~30 s overlapping candidate clips;
                   near-empty windows and exact duplicates are dropped before any scoring.
  3. Lexical     - Okapi BM25 over every window of every selected video (exact-term match).
  4. Semantic    - cosine similarity from a small ONNX embedding model (bge-small, ~33 MB).
                   Window vectors are computed once per video and stored, so a query only embeds
                   the query text.
  5. Fusion      - weighted sum of the two min-max-normalised scores, lightly scaled by ASR
                   confidence so clips from garbled speech rank lower.
  6. Selection   - best-first; skips clips overlapping a chosen one, near-duplicate text (e.g. the
                   same content re-uploaded), and caps clips per video.

If the embedding model cannot be loaded (offline, not installed) it degrades to BM25 only.
"""

import logging
import math
import re
import threading
from collections import Counter
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger(__name__)

_TOKEN = re.compile(r"\w+", re.UNICODE)
_STOP = frozenset(
    "a an the and or but if of to in on at by for with from as is are was were be been it its this that "
    "these those i you he she we they them his her our your their so not no do does did have has had "
    "will would can could just about into than then there here what which who whom how".split()
)

SEMANTIC_WEIGHT = 0.65
LEXICAL_WEIGHT = 0.35
MIN_CONTENT_TOKENS = 8  # windows with less substance than this are not worth ranking
DUPLICATE_JACCARD = 0.8  # clips whose word sets overlap more than this count as the same content


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1]


@dataclass
class Window:
    source_id: str
    start: float
    end: float
    text: str
    confidence: float | None
    tokens: list[str] = field(repr=False, default_factory=list)
    vec: list[float] | None = field(repr=False, default=None)
    video_end: float = 0.0


def build_windows(source_id: str, segments: list[dict], window_sec: float = 30.0) -> list[Window]:
    """Group consecutive segments into windows of >= window_sec, advancing by ~half a window."""
    windows: list[Window] = []
    seen: set[str] = set()
    video_end = float(segments[-1]["end"]) if segments else 0.0
    n, i = len(segments), 0
    while i < n:
        j, start = i, float(segments[i]["start"])
        while j < n and float(segments[j]["end"]) - start < window_sec:
            j += 1
        last = min(j, n - 1)
        chunk = segments[i : last + 1]
        text = " ".join(s["text"].strip() for s in chunk).strip()
        tokens = tokenize(text)
        if len(tokens) >= MIN_CONTENT_TOKENS and text not in seen:
            seen.add(text)
            confs = [s["confidence"] for s in chunk if s.get("confidence") is not None]
            windows.append(
                Window(
                    source_id,
                    round(start, 2),
                    round(float(chunk[-1]["end"]), 2),
                    text,
                    sum(confs) / len(confs) if confs else None,
                    tokens,
                    video_end=video_end,
                )
            )
        if last >= n - 1:
            break
        # next window starts about half a window later (always moves forward)
        nxt = i + 1
        while nxt < last and float(segments[nxt]["start"]) - start < window_sec / 2:
            nxt += 1
        i = nxt
    return windows


def bm25_scores(query_tokens: list[str], docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> list[float]:
    n = len(docs)
    if n == 0 or not query_tokens:
        return [0.0] * n
    avgdl = (sum(len(d) for d in docs) / n) or 1.0
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    idf = {t: math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in set(query_tokens) if df[t]}
    scores = []
    for d in docs:
        tf = Counter(d)
        s = 0.0
        for t, w in idf.items():
            f = tf.get(t, 0)
            if f:
                s += w * f * (k1 + 1) / (f + k1 * (1 - b + b * len(d) / avgdl))
        scores.append(s)
    return scores


def _minmax(values: list[float], flat: float = 0.0) -> list[float]:
    """Scale to 0-1. If all values are equal there is no spread to rank by: return `flat` for all."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [flat] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


class Embedder:
    """Lazy wrapper around fastembed's ONNX TextEmbedding. `model=None` disables semantic scoring."""

    def __init__(self, model: str | None, cache_dir: str | None = None):
        self.model_name = model or None
        self.cache_dir = cache_dir  # default would be the OS temp dir, which gets cleaned up
        self._model = None
        self._failed = self.model_name is None
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return not self._failed

    def load(self) -> bool:
        with self._lock:
            if self._model is not None:
                return True
            if self._failed:
                return False
            try:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self.model_name, cache_dir=self.cache_dir)
                return True
            except Exception:  # noqa: BLE001 - offline / not installed -> fall back to BM25
                log.exception("Embedding model %s unavailable; using BM25 only", self.model_name)
                self._failed = True
                return False

    def embed_docs(self, texts: list[str]) -> list[list[float]]:
        # 4 decimals: negligible for cosine ranking, ~half the storage of full floats
        return [[round(float(x), 4) for x in v] for v in self._model.embed(texts, batch_size=32)]

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in next(iter(self._model.query_embed(text)))]


@dataclass
class RankedClip:
    window: Window
    score: float
    lexical: float
    semantic: float | None
    features: dict[str, float] = field(default_factory=dict)


def rank_windows(
    windows: list[Window],
    query: str,
    embedder: Embedder | None,
    top_k: int = 10,
    per_video_max: int | None = 3,
    max_overlap: float = 0.3,
    model=None,
) -> tuple[list[RankedClip], str]:
    """Return (best distinct clips, method); method is 'learned', 'hybrid' or 'bm25'.

    `model` is an optional trained LearnedRanker; it replaces the fixed 35/65 blend when the
    semantic signal is available. Windows that already carry a stored `vec` are not re-embedded;
    freshly computed vectors are written back onto the windows so the caller can persist them.
    """
    if not windows:
        return [], "bm25"

    q_tokens = tokenize(query)
    q_set = set(q_tokens)
    raw_lex = bm25_scores(q_tokens, [w.tokens for w in windows])
    lexical = _minmax(raw_lex, flat=1.0 if max(raw_lex) > 0 else 0.0)  # all-equal but matching = match

    semantic: list[float] | None = None
    cosine: list[float] = [0.0] * len(windows)
    method = "bm25"
    if embedder is not None and embedder.load():
        todo = [w for w in windows if w.vec is None]
        if todo:
            for w, v in zip(todo, embedder.embed_docs([w.text for w in todo])):
                w.vec = v
        matrix = np.asarray([w.vec for w in windows], dtype=np.float32)
        q = np.asarray(embedder.embed_query(query), dtype=np.float32)
        cosine = (matrix @ q).tolist()  # vectors are L2-normalised -> cosine
        semantic = _minmax(cosine, flat=0.5)
        method = "hybrid"

    feats: list[dict[str, float]] = []
    for i, w in enumerate(windows):
        span = max(w.end - w.start, 1.0)
        feats.append(
            {
                "lexical": lexical[i],
                "semantic": 0.0 if semantic is None else semantic[i],
                "bm25_log": math.log1p(raw_lex[i]),
                "cosine": cosine[i],
                "coverage": len(q_set & set(w.tokens)) / len(q_set) if q_set else 0.0,
                "density": min(len(w.tokens) / span / 3.0, 1.0),
                "confidence": w.confidence if w.confidence is not None else 0.8,
                "position": w.start / w.video_end if w.video_end else 0.0,
                "length": min(span / 60.0, 1.0),
            }
        )

    learned = None
    if model is not None and semantic is not None:  # the model was trained with the semantic signal
        learned = model.score(np.asarray([[f[n] for n in model.features] for f in feats]))
        method = "learned"

    ranked: list[RankedClip] = []
    for i, w in enumerate(windows):
        if learned is not None:
            score = float(learned[i])
        else:
            base = lexical[i] if semantic is None else LEXICAL_WEIGHT * lexical[i] + SEMANTIC_WEIGHT * semantic[i]
            score = base * (0.85 + 0.15 * feats[i]["confidence"])
        ranked.append(RankedClip(w, round(score, 4), round(lexical[i], 4),
                                 None if semantic is None else round(semantic[i], 4),
                                 {k: round(v, 4) for k, v in feats[i].items()}))
    ranked.sort(key=lambda c: c.score, reverse=True)

    picked: list[RankedClip] = []
    per_video: Counter[str] = Counter()
    for c in ranked:
        if c.score <= 0:
            break
        w = c.window
        if per_video_max and per_video[w.source_id] >= per_video_max:
            continue
        if any(_overlap(w, p.window) > max_overlap for p in picked if p.window.source_id == w.source_id):
            continue
        if any(_jaccard(w.tokens, p.window.tokens) > DUPLICATE_JACCARD for p in picked):
            continue  # same content again (re-upload / repeated passage), even from another video
        picked.append(c)
        per_video[w.source_id] += 1
        if len(picked) >= top_k:
            break
    return picked, method


def _overlap(a: Window, b: Window) -> float:
    inter = min(a.end, b.end) - max(a.start, b.start)
    shorter = min(a.end - a.start, b.end - b.start)
    return max(inter, 0.0) / shorter if shorter > 0 else 0.0


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    union = len(sa | sb)
    return len(sa & sb) / union if union else 0.0
