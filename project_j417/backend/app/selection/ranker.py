"""Relevance ranking of video segments for a topic / audience.

Pipeline (all CPU, no GPU needed):
  1. Windowing   - merge consecutive ASR segments into ~30 s overlapping candidate clips.
  2. Lexical     - Okapi BM25 over every window of every selected video (exact-term match).
  3. Semantic    - cosine similarity from a small ONNX embedding model (bge-small, ~33 MB).
  4. Fusion      - weighted sum of the two min-max-normalised scores, lightly scaled by ASR
                   confidence so clips from garbled speech rank lower.
  5. Selection   - greedy pick best-first, dropping clips that overlap one already chosen and
                   capping clips per video so one long video cannot fill the whole list.

If the embedding model cannot be loaded (offline, not installed) it degrades to BM25 only.
"""

import hashlib
import logging
import math
import re
import threading
from collections import Counter
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

_TOKEN = re.compile(r"\w+", re.UNICODE)
_STOP = frozenset(
    "a an the and or but if of to in on at by for with from as is are was were be been it its this that "
    "these those i you he she we they them his her our your their so not no do does did have has had "
    "will would can could just about into than then there here what which who whom how".split()
)

SEMANTIC_WEIGHT = 0.65
LEXICAL_WEIGHT = 0.35


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


def build_windows(source_id: str, segments: list[dict], window_sec: float = 30.0) -> list[Window]:
    """Group consecutive segments into windows of >= window_sec, advancing by ~half a window."""
    windows: list[Window] = []
    n, i = len(segments), 0
    while i < n:
        j, start = i, float(segments[i]["start"])
        while j < n and float(segments[j]["end"]) - start < window_sec:
            j += 1
        last = min(j, n - 1)
        chunk = segments[i : last + 1]
        text = " ".join(s["text"].strip() for s in chunk).strip()
        if text:
            confs = [s["confidence"] for s in chunk if s.get("confidence") is not None]
            windows.append(
                Window(
                    source_id,
                    round(start, 2),
                    round(float(chunk[-1]["end"]), 2),
                    text,
                    sum(confs) / len(confs) if confs else None,
                    tokenize(text),
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


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.0] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


class Embedder:
    """Lazy wrapper around fastembed's ONNX TextEmbedding. `model=None` disables semantic scoring."""

    def __init__(self, model: str | None, cache_dir: str | None = None):
        self.model_name = model or None
        self.cache_dir = cache_dir  # default would be the OS temp dir, which gets cleaned up
        self._model = None
        self._failed = self.model_name is None
        self._lock = threading.Lock()
        self._cache: dict[str, list[float]] = {}

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
        keys = [hashlib.sha1(t.encode()).hexdigest() for t in texts]
        missing = [(k, t) for k, t in zip(keys, texts) if k not in self._cache]
        if missing:
            vecs = self._model.embed([t for _, t in missing], batch_size=64)
            for (k, _), v in zip(missing, vecs):
                self._cache[k] = [float(x) for x in v]
            if len(self._cache) > 50_000:  # crude bound
                self._cache.clear()
                return self.embed_docs(texts)
        return [self._cache[k] for k in keys]

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in next(iter(self._model.query_embed(text)))]


@dataclass
class RankedClip:
    window: Window
    score: float
    lexical: float
    semantic: float | None


def rank_windows(
    windows: list[Window],
    query: str,
    embedder: Embedder | None,
    top_k: int = 10,
    per_video_max: int | None = 3,
    max_overlap: float = 0.3,
) -> tuple[list[RankedClip], str]:
    """Return (best non-overlapping clips, method) where method is 'hybrid' or 'bm25'."""
    if not windows:
        return [], "bm25"

    lexical = _minmax(bm25_scores(tokenize(query), [w.tokens for w in windows]))

    semantic: list[float] | None = None
    method = "bm25"
    if embedder is not None and embedder.load():
        doc_vecs = embedder.embed_docs([w.text for w in windows])
        q = embedder.embed_query(query)
        cos = [sum(a * b for a, b in zip(q, d)) for d in doc_vecs]  # vectors are L2-normalised
        semantic = _minmax(cos)
        method = "hybrid"

    ranked: list[RankedClip] = []
    for i, w in enumerate(windows):
        base = lexical[i] if semantic is None else LEXICAL_WEIGHT * lexical[i] + SEMANTIC_WEIGHT * semantic[i]
        quality = 0.85 + 0.15 * (w.confidence if w.confidence is not None else 0.8)
        ranked.append(RankedClip(w, round(base * quality, 4), round(lexical[i], 4),
                                 None if semantic is None else round(semantic[i], 4)))
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
        picked.append(c)
        per_video[w.source_id] += 1
        if len(picked) >= top_k:
            break
    return picked, method


def _overlap(a: Window, b: Window) -> float:
    inter = min(a.end, b.end) - max(a.start, b.start)
    shorter = min(a.end - a.start, b.end - b.start)
    return max(inter, 0.0) / shorter if shorter > 0 else 0.0
