"""Shared FastAPI dependencies."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oar.auth.api_key import extract_bearer_token, extract_key_prefix, verify_api_key
from oar.database import async_session
from oar.models.api_key import ApiKey
from oar.models.publisher import Publisher


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def get_current_api_key(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    """Resolve and validate an API key. Returns the ApiKey row."""
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    prefix = extract_key_prefix(token)
    if not prefix:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")

    result = await db.execute(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.status == "active")
        .join(Publisher)
    )
    api_key = result.scalar_one_or_none()

    if not api_key or not verify_api_key(token, api_key.key_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or inactive API key")

    return api_key


async def get_current_publisher(
    api_key: ApiKey = Depends(get_current_api_key),
    db: AsyncSession = Depends(get_db),
) -> Publisher:
    """Authenticate via API key and return the owning publisher."""
    result = await db.execute(select(Publisher).where(Publisher.id == api_key.publisher_id))
    publisher = result.scalar_one_or_none()
    if not publisher:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Publisher not found")
    return publisher
