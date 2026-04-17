"""Pydantic schemas for publisher request/response."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PublisherCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*$", max_length=255)
    email: str = Field(..., max_length=255)
    url: str | None = Field(None, max_length=512)


class PublisherResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    email: str
    url: str | None
    verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PublisherCreateResponse(PublisherResponse):
    """Returned only on creation — includes the raw API key (shown once)."""
    api_key: str


class PublisherSummary(BaseModel):
    slug: str
    name: str
    verified: bool

    model_config = {"from_attributes": True}
