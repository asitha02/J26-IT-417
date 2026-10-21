import asyncio
import hashlib
import re
import time

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import Settings, get_settings
from app.selection import learned
from app.selection.clean import clean_segments
from app.selection.ranker import Embedder, build_windows, rank_windows
from app.selection.schemas import (
    Clip,
    LabelIn,
    LabelStats,
    LibraryItem,
    ModelInfo,
    RankRequest,
    RankResponse,
)
from app.transcription.repository import Repository

router = APIRouter(prefix="/api/segments", tags=["segment-selection"])

_YT = re.compile(r"(?:youtube\.com|youtu\.be)", re.I)
_model_cache: dict[str, tuple[float, learned.LearnedRanker]] = {}


def _model_path(settings: Settings):
    return settings.data_dir / "models" / "ranker.json"


def load_model(settings: Settings) -> learned.LearnedRanker | None:
    """The trained ranker, re-read only when the file changes (a retrain takes effect at once)."""
    path = _model_path(settings)
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    hit = _model_cache.get(str(path))
    if hit is None or hit[0] != mtime:
        _model_cache[str(path)] = (mtime, learned.LearnedRanker.load(path))
    return _model_cache[str(path)][1]


def _group(query: str, audience: str | None) -> str:
    return f"{query.strip().lower()}|{(audience or '').strip().lower()}"


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


def get_embedder(request: Request) -> Embedder | None:
    return getattr(request.app.state, "embedder", None)


def _latest_per_video(docs: list[dict]) -> list[dict]:
    """A video may be transcribed by several ASR models - keep the newest transcript of each."""
    best: dict[str, dict] = {}
    for d in docs:
        cur = best.get(d["source_id"])
        if cur is None or d.get("created_at") and d["created_at"] > cur.get("created_at", d["created_at"]):
            best[d["source_id"]] = d
    return list(best.values())


def _embedding_key(doc: dict, embedder: Embedder, window_sec: float) -> str:
    return f"{doc['_id']}__{embedder.model_name}__{int(window_sec)}"


def _signature(windows: list) -> str:
    """Fingerprint of the window texts, so stored vectors are discarded if cleaning/ASR changes."""
    h = hashlib.sha1()
    for w in windows:
        h.update(f"{w.start}|{w.end}|{w.text}\n".encode())
    return h.hexdigest()


def _watch_url(doc: dict, start: float) -> str:
    url = doc["source_url"]
    if _YT.search(url):
        return f"https://www.youtube.com/watch?v={doc['source_id']}&t={int(start)}s"
    return f"{url}#t={int(start)}"


@router.get("/library", response_model=list[LibraryItem])
async def library(repo: Repository = Depends(get_repo)):
    docs = _latest_per_video(await repo.list_transcripts())
    return [
        LibraryItem(
            source_id=d["source_id"],
            title=d.get("title"),
            source_url=d["source_url"],
            duration_sec=d.get("duration_sec"),
            language=d.get("language"),
            segments=len(d.get("segments", [])),
        )
        for d in docs
    ]


@router.post("/rank", response_model=RankResponse)
async def rank(
    body: RankRequest,
    repo: Repository = Depends(get_repo),
    embedder: Embedder | None = Depends(get_embedder),
    settings: Settings = Depends(get_settings),
):
    started = time.perf_counter()
    docs = _latest_per_video(await repo.list_transcripts(body.source_ids))
    if not docs:
        raise HTTPException(404, "No transcripts to search - transcribe some videos first.")

    query = body.query.strip()
    if body.audience and body.audience.strip():
        query = f"{query}. Suitable for {body.audience.strip()}"

    def make_windows():
        return {
            d["source_id"]: build_windows(d["source_id"], clean_segments(d["segments"]), body.window_sec)
            for d in docs
        }

    per_doc = await asyncio.to_thread(make_windows)
    windows = [w for ws in per_doc.values() for w in ws]

    # Reuse window vectors stored from earlier queries - only new videos need embedding.
    use_store = embedder is not None and embedder.available
    keys = {d["source_id"]: _embedding_key(d, embedder, body.window_sec) for d in docs} if use_store else {}
    fresh: set[str] = set()
    if use_store:
        for d in docs:
            sid, ws = d["source_id"], per_doc[d["source_id"]]
            stored = await repo.get_embeddings(keys[sid])
            if stored and stored.get("sig") == _signature(ws) and len(stored["vectors"]) == len(ws):
                for w, v in zip(ws, stored["vectors"]):
                    w.vec = v
            else:
                fresh.add(sid)

    model = load_model(settings) if body.ranker == "auto" else None
    picked, method = await asyncio.to_thread(
        rank_windows, windows, query, embedder, body.top_k, body.per_video_max, 0.3, model
    )

    if method in ("hybrid", "learned"):
        for sid in fresh:
            ws = per_doc[sid]
            if ws and all(w.vec is not None for w in ws):
                await repo.save_embeddings(keys[sid], _signature(ws), [w.vec for w in ws])
    by_id = {d["source_id"]: d for d in docs}
    clips = [
        Clip(
            rank=i,
            source_id=c.window.source_id,
            title=by_id[c.window.source_id].get("title"),
            source_url=by_id[c.window.source_id]["source_url"],
            watch_url=_watch_url(by_id[c.window.source_id], c.window.start),
            start=c.window.start,
            end=c.window.end,
            score=c.score,
            lexical_score=c.lexical,
            semantic_score=c.semantic,
            text=c.window.text,
            features=c.features,
        )
        for i, c in enumerate(picked, 1)
    ]
    return RankResponse(
        query=body.query,
        audience=body.audience,
        method=method,
        embedding_model=embedder.model_name if method != "bm25" and embedder else None,
        videos_searched=len(docs),
        windows_searched=len(windows),
        elapsed_sec=round(time.perf_counter() - started, 3),
        clips=clips,
    )


# ---------------------------------------------------------------- ranker training

def _label_stats(labels: list[dict]) -> LabelStats:
    pos = sum(1 for l in labels if l["label"] == 1)
    neg = len(labels) - pos
    queries = len({l["group"] for l in labels})
    needs = None
    if len(labels) < learned.MIN_LABELS or pos < learned.MIN_POSITIVES or neg < learned.MIN_NEGATIVES or queries < learned.MIN_QUERIES:
        needs = (
            f"Need {learned.MIN_LABELS}+ labels ({learned.MIN_POSITIVES}+ relevant, {learned.MIN_NEGATIVES}+ not relevant) "
            f"across {learned.MIN_QUERIES}+ different queries."
        )
    return LabelStats(labels=len(labels), positives=pos, negatives=neg, queries=queries,
                      ready_to_train=needs is None, needs=needs)


@router.put("/labels", status_code=204)
async def set_label(body: LabelIn, repo: Repository = Depends(get_repo)):
    """Mark a ranked clip relevant (1) / not relevant (0); null removes the label."""
    group = _group(body.query, body.audience)
    label_id = f"{group}|{body.source_id}|{round(body.start, 1)}"
    if body.label is None:
        await repo.delete_label(label_id)
        return
    await repo.upsert_label(
        {
            "_id": label_id,
            "group": group,
            "query": body.query,
            "audience": body.audience,
            "source_id": body.source_id,
            "start": body.start,
            "end": body.end,
            "label": body.label,
            "features": body.features,
        }
    )


@router.get("/labels")
async def export_labels(repo: Repository = Depends(get_repo)):
    """All labelled clips (training data) as JSON."""
    return await repo.list_labels()


@router.get("/labels/stats", response_model=LabelStats)
async def label_stats(repo: Repository = Depends(get_repo)):
    return _label_stats(await repo.list_labels())


@router.post("/train", response_model=ModelInfo)
async def train_ranker(repo: Repository = Depends(get_repo), settings: Settings = Depends(get_settings)):
    """Fit the learned ranker on all labels, report held-out metrics, and activate it."""
    labels = await repo.list_labels()
    try:
        model = await asyncio.to_thread(
            learned.train, [{"features": l["features"], "label": l["label"], "group": l["group"]} for l in labels]
        )
    except learned.TrainingError as exc:
        raise HTTPException(422, str(exc)) from exc
    model.save(_model_path(settings))
    return ModelInfo(trained=True, trained_at=model.trained_at, report=model.report)


@router.get("/model", response_model=ModelInfo)
async def model_info(settings: Settings = Depends(get_settings)):
    model = load_model(settings)
    if model is None:
        return ModelInfo(trained=False)
    return ModelInfo(trained=True, trained_at=model.trained_at, report=model.report)
