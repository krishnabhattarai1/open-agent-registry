"""Business logic for API key management and usage stats."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from oar.auth.api_key import create_api_key
from oar.models.api_key import ApiKey, ApiKeyUsageLog
from oar.models.publisher import Publisher
from oar.schemas.api_key import ApiKeyCreate, UsageLogPage, UsageSummary


async def create_key(
    db: AsyncSession, publisher: Publisher, data: ApiKeyCreate
) -> tuple[ApiKey, str]:
    """Create a new API key for the publisher. Returns (ApiKey, raw_key)."""
    raw_key, key_hash, prefix = create_api_key()
    key = ApiKey(
        id=uuid.uuid4(),
        publisher_id=publisher.id,
        name=data.name,
        key_hash=key_hash,
        key_prefix=prefix,
        status="active",
        expires_at=data.expires_at,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key, raw_key


async def list_keys(db: AsyncSession, publisher: Publisher) -> list[ApiKey]:
    """List all non-deleted keys for a publisher."""
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.publisher_id == publisher.id, ApiKey.status != "deleted")
        .order_by(desc(ApiKey.created_at))
    )
    return list(result.scalars().all())


async def get_key(
    db: AsyncSession, key_id: uuid.UUID, publisher: Publisher
) -> ApiKey | None:
    """Get a specific key belonging to the publisher."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.publisher_id == publisher.id,
            ApiKey.status != "deleted",
        )
    )
    return result.scalar_one_or_none()


async def set_key_status(
    db: AsyncSession, key: ApiKey, new_status: str
) -> ApiKey:
    """Enable or disable a key."""
    key.status = new_status
    await db.commit()
    await db.refresh(key)
    return key


async def delete_key(db: AsyncSession, key: ApiKey) -> None:
    """Soft-delete a key — marks as deleted, preserves usage history."""
    key.status = "deleted"
    await db.commit()


async def get_usage_summary(
    db: AsyncSession, key: ApiKey
) -> UsageSummary:
    """Aggregate usage stats for a single key."""
    # Main aggregates
    agg = await db.execute(
        select(
            func.count().label("total_requests"),
            func.coalesce(func.sum(ApiKeyUsageLog.request_bytes), 0).label("total_request_bytes"),
            func.coalesce(func.sum(ApiKeyUsageLog.response_bytes), 0).label("total_response_bytes"),
            func.coalesce(func.sum(ApiKeyUsageLog.estimated_tokens), 0).label("total_estimated_tokens"),
            func.coalesce(func.avg(ApiKeyUsageLog.duration_ms), 0).label("avg_duration_ms"),
            func.count().filter(
                ApiKeyUsageLog.status_code.between(200, 299)
            ).label("requests_2xx"),
            func.count().filter(
                ApiKeyUsageLog.status_code.between(400, 499)
            ).label("requests_4xx"),
            func.count().filter(
                ApiKeyUsageLog.status_code.between(500, 599)
            ).label("requests_5xx"),
        ).where(ApiKeyUsageLog.api_key_id == key.id)
    )
    row = agg.one()

    # Top 5 endpoints by call count
    top_eps = await db.execute(
        select(
            ApiKeyUsageLog.endpoint,
            ApiKeyUsageLog.method,
            func.count().label("calls"),
            func.sum(ApiKeyUsageLog.response_bytes).label("bytes_out"),
        )
        .where(ApiKeyUsageLog.api_key_id == key.id)
        .group_by(ApiKeyUsageLog.endpoint, ApiKeyUsageLog.method)
        .order_by(desc("calls"))
        .limit(5)
    )

    return UsageSummary(
        api_key_id=key.id,
        key_name=key.name,
        key_prefix=key.key_prefix,
        status=key.status,
        total_requests=row.total_requests,
        total_request_bytes=row.total_request_bytes,
        total_response_bytes=row.total_response_bytes,
        total_estimated_tokens=row.total_estimated_tokens,
        avg_duration_ms=float(row.avg_duration_ms),
        requests_2xx=row.requests_2xx,
        requests_4xx=row.requests_4xx,
        requests_5xx=row.requests_5xx,
        last_used_at=key.last_used_at,
        top_endpoints=[
            {
                "endpoint": r.endpoint,
                "method": r.method,
                "calls": r.calls,
                "bytes_out": r.bytes_out or 0,
            }
            for r in top_eps.all()
        ],
    )


async def get_usage_logs(
    db: AsyncSession,
    key: ApiKey,
    page: int = 1,
    per_page: int = 50,
) -> UsageLogPage:
    """Paginated raw usage log for a key, newest first."""
    offset = (page - 1) * per_page

    total_result = await db.execute(
        select(func.count()).where(ApiKeyUsageLog.api_key_id == key.id)
    )
    total = total_result.scalar_one()

    logs_result = await db.execute(
        select(ApiKeyUsageLog)
        .where(ApiKeyUsageLog.api_key_id == key.id)
        .order_by(desc(ApiKeyUsageLog.called_at))
        .offset(offset)
        .limit(per_page)
    )
    logs = list(logs_result.scalars().all())

    return UsageLogPage(data=logs, total=total, page=page, per_page=per_page)
