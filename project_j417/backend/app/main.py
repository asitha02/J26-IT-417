import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.config import get_settings
from app.selection.ranker import Embedder
from app.selection.router import router as selection_router
from app.transcription.repository import Repository
from app.transcription.router import router as transcription_router
from app.transcription.transcriber import Transcriber

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    owns_db = getattr(app.state, "repo", None) is None
    if owns_db:  # tests inject their own repo/transcriber
        app.state.repo = Repository(await db.connect(settings))
        await app.state.repo.ensure_indexes()
        await app.state.repo.fail_unfinished()
    if getattr(app.state, "transcriber", None) is None:
        app.state.transcriber = Transcriber(settings.asr())
        if settings.preload_model:  # warm the model in the background so job #1 starts fast
            app.state.warmup = asyncio.create_task(asyncio.to_thread(app.state.transcriber.load))
    if getattr(app.state, "embedder", None) is None:
        model = settings.embed_model.strip()
        app.state.embedder = Embedder(
            None if model.lower() in ("", "none") else model, str(settings.data_dir / "models")
        )
        if app.state.embedder.available and settings.preload_model:
            asyncio.create_task(asyncio.to_thread(app.state.embedder.load))
    yield
    if owns_db:
        await db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Cross-Video Knowledge Extraction - Transcription API", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(transcription_router)
    app.include_router(selection_router)

    @app.get("/api/health")
    async def health():
        cfg = app.state.transcriber.cfg
        return {"status": "ok", "model": cfg.model, "device": cfg.device}

    return app


app = create_app()
