from fastapi import APIRouter

from app.api.routes import export, fusion, generate, health, ingest, kb, translate

api_router = APIRouter()

for route in (
    health,
    ingest,
    fusion,
    kb,
    translate,
    generate,
    export,
):
    api_router.include_router(route.router)