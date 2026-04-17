"""FastAPI application factory."""

import os

from fastapi import FastAPI

from oar.api.router import api_router
from oar.middleware.usage import UsageLoggingMiddleware

PORT = int(os.getenv("OAR_PORT", "7430"))


def create_app() -> FastAPI:
    app = FastAPI(
        title="Open Agent Registry",
        description="Token-optimized AI agent registry and discovery for agent-to-agent communication",
        version="0.1.0",
        servers=[{"url": f"http://localhost:{PORT}", "description": "Local"}],
    )
    app.include_router(api_router)
    app.add_middleware(UsageLoggingMiddleware)
    return app


app = create_app()
