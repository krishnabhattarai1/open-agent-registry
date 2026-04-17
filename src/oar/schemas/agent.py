"""Pydantic schemas for agent request/response (verbose and compact)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from oar.schemas.publisher import PublisherSummary

PROTOCOL = Literal["a2a", "mcp", "acp", "rest", "grpc"]
AUTH_TYPE = Literal["bearer", "api_key", "oauth2", "none"]
STATUS = Literal["active", "deprecated", "archived"]


class CapabilityIn(BaseModel):
    code: str = Field(..., description="Taxonomy capability code e.g. code.review")
    input_types: list[str] | None = None
    output_types: list[str] | None = None


class EndpointIn(BaseModel):
    protocol: PROTOCOL
    url: str = Field(..., max_length=512)
    auth_type: AUTH_TYPE | None = None
    auth_config: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*$", max_length=255)
    description: str
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+.*$")
    status: STATUS = "active"
    homepage_url: str | None = Field(None, max_length=512)
    repository_url: str | None = Field(None, max_length=512)
    license: str | None = Field(None, max_length=100)
    tags: list[str] = []
    capabilities: list[CapabilityIn] = []
    endpoints: list[EndpointIn] = []


class AgentUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    version: str | None = Field(None, pattern=r"^\d+\.\d+\.\d+.*$")
    status: STATUS | None = None
    homepage_url: str | None = None
    repository_url: str | None = None
    license: str | None = None
    tags: list[str] | None = None
    capabilities: list[CapabilityIn] | None = None
    endpoints: list[EndpointIn] | None = None


class CapabilityResponse(BaseModel):
    code: str
    input_types: list[str] | None
    output_types: list[str] | None

    model_config = {"from_attributes": True}


class EndpointResponse(BaseModel):
    protocol: str
    url: str
    auth_type: str | None
    auth_config: dict[str, Any] | None

    model_config = {"from_attributes": True}


class AgentResponse(BaseModel):
    id: uuid.UUID
    short_id: str
    name: str
    slug: str
    publisher: PublisherSummary
    description: str
    version: str
    status: str
    homepage_url: str | None
    repository_url: str | None
    license: str | None
    tags: list[str]
    capabilities: list[CapabilityResponse]
    endpoints: list[EndpointResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_agent(cls, agent: Any) -> "AgentResponse":
        return cls(
            id=agent.id,
            short_id=agent.short_id,
            name=agent.name,
            slug=agent.slug,
            publisher=PublisherSummary.model_validate(agent.publisher),
            description=agent.description,
            version=agent.version,
            status=agent.status,
            homepage_url=agent.homepage_url,
            repository_url=agent.repository_url,
            license=agent.license,
            tags=[t.name for t in agent.tags],
            capabilities=[CapabilityResponse.model_validate(c) for c in agent.capabilities],
            endpoints=[EndpointResponse.model_validate(e) for e in agent.endpoints],
            created_at=agent.created_at,
            updated_at=agent.updated_at,
        )


class AgentListResponse(BaseModel):
    data: list[AgentResponse]
    meta: dict[str, int]


class AgentVersionResponse(BaseModel):
    id: uuid.UUID
    version: str
    manifest_snapshot: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
