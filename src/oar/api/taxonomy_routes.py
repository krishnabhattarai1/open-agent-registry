"""GET /v1/taxonomy — capability codes (aggressively cached)."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from oar.taxonomy import get_taxonomy_compact

router = APIRouter(prefix="/v1", tags=["taxonomy"])


@router.get("/taxonomy")
async def get_taxonomy() -> JSONResponse:
    """Return the capability taxonomy. Cache for 7 days — changes rarely."""
    data = get_taxonomy_compact()
    return JSONResponse(
        content=data,
        headers={"Cache-Control": "public, max-age=604800"},
    )
