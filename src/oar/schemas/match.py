"""Pydantic schemas for the match query — the primary agent-facing discovery endpoint."""

from typing import Any

from pydantic import BaseModel, Field


class MatchQuery(BaseModel):
    """Structured capability query. Returns compact results sorted by score."""

    need: list[str] = Field(..., min_length=1, description="Required capability codes (all must match)")
    want: list[str] | None = Field(None, description="Preferred codes (boost score)")
    proto: str | None = Field(None, description="Required protocol: a2a, mcp, acp, rest, grpc")
    auth: list[str] | None = Field(None, description="Acceptable auth types (any match)")
    io_in: str | None = Field(None, description="Input MIME type the caller will send")
    limit: int = Field(5, ge=1, le=50)
    min_score: int = Field(0, ge=0, le=100)


class CompactAgentResult(BaseModel):
    """Single agent in a compact match response (~40-60 tokens)."""
    id: str
    n: str          # name
    c: list[str]    # capabilities
    p: str          # protocol (primary)
    v: str          # version
    s: int          # score 0-100


class MatchResponse(BaseModel):
    """Compact match response envelope."""
    r: list[CompactAgentResult]   # results
    t: int                         # total
    ttl: int                       # cache TTL seconds
    etag: str | None = Field(None, alias="_etag")

    model_config = {"populate_by_name": True}


class BatchFetchRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=20)
    fields: list[str] | None = None


class CompactConnectInfo(BaseModel):
    """Minimal connection info for Stage 2 fetch."""
    id: str
    ep: str         # endpoint URL
    auth: dict[str, Any] | None = None
