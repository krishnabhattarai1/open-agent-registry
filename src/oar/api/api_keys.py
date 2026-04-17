"""API key management endpoints.

All routes require the publisher's existing active API key for auth.
Keys are scoped to the authenticated publisher — you can only manage your own.

Routes:
  POST   /v1/keys                    create a new key
  GET    /v1/keys                    list all your keys
  GET    /v1/keys/{key_id}           get a specific key
  PATCH  /v1/keys/{key_id}/status    enable or disable
  DELETE /v1/keys/{key_id}           soft-delete
  GET    /v1/keys/{key_id}/usage     aggregated usage stats
  GET    /v1/keys/{key_id}/logs      paginated raw usage log
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from oar.dependencies import get_current_publisher, get_db
from oar.models.publisher import Publisher
from oar.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    ApiKeyStatusUpdate,
    UsageLogPage,
    UsageSummary,
)
from oar.services import api_key_service

router = APIRouter(prefix="/v1/keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    publisher: Publisher = Depends(get_current_publisher),
) -> ApiKeyCreateResponse:
    """Create a new API key. The raw key is shown once — store it safely."""
    key, raw_key = await api_key_service.create_key(db, publisher, data)
    return ApiKeyCreateResponse(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        status=key.status,
        created_at=key.created_at,
        last_used_at=key.last_used_at,
        expires_at=key.expires_at,
        api_key=raw_key,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    publisher: Publisher = Depends(get_current_publisher),
) -> list[ApiKeyResponse]:
    """List all active and disabled keys for your publisher."""
    keys = await api_key_service.list_keys(db, publisher)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    publisher: Publisher = Depends(get_current_publisher),
) -> ApiKeyResponse:
    key = await api_key_service.get_key(db, key_id, publisher)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return ApiKeyResponse.model_validate(key)


@router.patch("/{key_id}/status", response_model=ApiKeyResponse)
async def update_key_status(
    key_id: uuid.UUID,
    data: ApiKeyStatusUpdate,
    db: AsyncSession = Depends(get_db),
    publisher: Publisher = Depends(get_current_publisher),
) -> ApiKeyResponse:
    """Enable or disable a key. Disabled keys are rejected at auth time."""
    key = await api_key_service.get_key(db, key_id, publisher)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    key = await api_key_service.set_key_status(db, key, data.status)
    return ApiKeyResponse.model_validate(key)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    publisher: Publisher = Depends(get_current_publisher),
) -> None:
    """Soft-delete a key. Usage history is preserved. This cannot be undone."""
    key = await api_key_service.get_key(db, key_id, publisher)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    await api_key_service.delete_key(db, key)


@router.get("/{key_id}/usage", response_model=UsageSummary)
async def get_key_usage(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    publisher: Publisher = Depends(get_current_publisher),
) -> UsageSummary:
    """Aggregated usage stats: request count, bytes in/out, estimated tokens, top endpoints."""
    key = await api_key_service.get_key(db, key_id, publisher)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return await api_key_service.get_usage_summary(db, key)


@router.get("/{key_id}/logs", response_model=UsageLogPage)
async def get_key_logs(
    key_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    publisher: Publisher = Depends(get_current_publisher),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
) -> UsageLogPage:
    """Paginated raw request log for a key, newest first."""
    key = await api_key_service.get_key(db, key_id, publisher)
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return await api_key_service.get_usage_logs(db, key, page=page, per_page=per_page)
