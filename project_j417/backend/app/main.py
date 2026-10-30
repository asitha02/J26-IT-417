import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymongo.errors import ConnectionFailure

from app import db
from app.cleaning.router import router as cleaning_router
from app.config import get_settings
from app.transcription.repository import Repository
from app.transcription.router import router as transcription_router
from app.transcription.transcriber import Transcriber
from app.videos.router import router as videos_router

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
    yield
    if owns_db:
        await db.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="YouTube transcripts - cleaned JSON", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(transcription_router)
    app.include_router(cleaning_router)
    app.include_router(videos_router)

    @app.exception_handler(ConnectionFailure)
    async def database_unreachable(_request: Request, exc: ConnectionFailure):
        logging.getLogger(__name__).warning("Database unreachable: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Cannot reach the database (MongoDB). Check your internet connection and that your IP "
                "address is allowed in MongoDB Atlas (Network Access), then try again."
            },
        )

    @app.get("/api/health")
    async def health():
        cfg = app.state.transcriber.cfg
        return {"status": "ok", "model": cfg.model, "device": cfg.device}

    return app


app = create_app()
