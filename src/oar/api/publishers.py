"""Publisher registration and profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from oar.dependencies import get_current_publisher, get_db
from oar.models.publisher import Publisher
from oar.schemas.publisher import PublisherCreate, PublisherCreateResponse, PublisherResponse
from oar.services import publisher_service

router = APIRouter(prefix="/v1/publishers", tags=["publishers"])


@router.post("", response_model=PublisherCreateResponse, status_code=status.HTTP_201_CREATED)
async def register_publisher(
    data: PublisherCreate,
    db: AsyncSession = Depends(get_db),
) -> PublisherCreateResponse:
    """Register a new publisher. Returns API key once — store it safely."""
    publisher, raw_key = await publisher_service.create_publisher(db, data)
    return PublisherCreateResponse(
        id=publisher.id,
        name=publisher.name,
        slug=publisher.slug,
        email=publisher.email,
        url=publisher.url,
        verified=publisher.verified,
        created_at=publisher.created_at,
        api_key=raw_key,
    )


@router.get("/{slug}", response_model=PublisherResponse)
async def get_publisher(
    slug: str,
    db: AsyncSession = Depends(get_db),
) -> PublisherResponse:
    publisher = await publisher_service.get_publisher_by_slug(db, slug)
    if not publisher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publisher not found")
    return PublisherResponse.model_validate(publisher)
