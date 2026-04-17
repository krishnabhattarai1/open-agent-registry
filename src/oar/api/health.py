"""Health and status endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/status")
async def status() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
