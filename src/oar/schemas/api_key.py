"""Pydantic schemas for API key management and usage stats."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Label e.g. 'production', 'ci'")
    expires_at: datetime | None = Field(None, description="Optional expiry (ISO 8601)")


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    status: str          # active | disabled | deleted
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreateResponse(ApiKeyResponse):
    """Returned once at creation — includes the raw key."""
    api_key: str = Field(..., description="Raw key — shown once, store safely")


class ApiKeyStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|disabled)$", description="active or disabled")


# ── Usage stats ───────────────────────────────────────────────────────────────

class UsageSummary(BaseModel):
    """Aggregated usage stats for a single API key."""
    api_key_id: uuid.UUID
    key_name: str
    key_prefix: str
    status: str
    total_requests: int
    total_request_bytes: int
    total_response_bytes: int
    total_estimated_tokens: int
    avg_duration_ms: float
    requests_2xx: int
    requests_4xx: int
    requests_5xx: int
    last_used_at: datetime | None
    # per-endpoint breakdown
    top_endpoints: list[dict]


class UsageLogEntry(BaseModel):
    """Single usage log row."""
    id: uuid.UUID
    endpoint: str
    method: str
    status_code: int
    request_bytes: int
    response_bytes: int
    estimated_tokens: int
    duration_ms: int
    called_at: datetime

    model_config = {"from_attributes": True}


class UsageLogPage(BaseModel):
    data: list[UsageLogEntry]
    total: int
    page: int
    per_page: int
