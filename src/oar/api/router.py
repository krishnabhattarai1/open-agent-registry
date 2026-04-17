"""Top-level API router — registers all sub-routers."""

from fastapi import APIRouter

from oar.api import agents, api_keys, health, match, publishers, taxonomy_routes

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(publishers.router)
api_router.include_router(agents.router)
api_router.include_router(match.router)
api_router.include_router(taxonomy_routes.router)
api_router.include_router(api_keys.router)
