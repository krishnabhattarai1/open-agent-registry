"""Publisher business logic."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oar.auth.api_key import create_api_key
from oar.models.api_key import ApiKey
from oar.models.publisher import Publisher
from oar.schemas.publisher import PublisherCreate


async def create_publisher(db: AsyncSession, data: PublisherCreate) -> tuple[Publisher, str]:
    """Create a publisher and a default API key. Returns (publisher, raw_api_key)."""
    raw_key, hashed, prefix = create_api_key()
    publisher = Publisher(
        name=data.name,
        slug=data.slug,
        email=data.email,
        url=data.url,
        # Keep legacy columns populated for backwards compat
        api_key_hash=hashed,
        api_key_prefix=prefix,
    )
    db.add(publisher)
    await db.flush()  # get publisher.id before creating the key

    # Insert the key into the new api_keys table
    default_key = ApiKey(
        id=uuid.uuid4(),
        publisher_id=publisher.id,
        name="default",
        key_hash=hashed,
        key_prefix=prefix,
        status="active",
    )
    db.add(default_key)
    await db.commit()
    await db.refresh(publisher)
    return publisher, raw_key


async def get_publisher_by_slug(db: AsyncSession, slug: str) -> Publisher | None:
    result = await db.execute(select(Publisher).where(Publisher.slug == slug))
    return result.scalar_one_or_none()
