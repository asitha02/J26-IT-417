from fastapi import APIRouter
from app.api.routes import health, ingest

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ingest.router)

from app.api.routes import health, ingest, fusion
api_router.include_router(fusion.router)

from app.api.routes import health, ingest, fusion, kb
api_router.include_router(kb.router)