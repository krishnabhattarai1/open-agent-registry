"""API key and usage models.

Multiple keys per publisher, each independently enabled/disabled/deleted.
Usage is logged per-request and aggregated per key.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oar.models import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    publisher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("publishers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "production", "ci-pipeline", "dev"
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )  # active | disabled | deleted
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    publisher = relationship("Publisher", back_populates="api_keys")
    usage_logs = relationship(
        "ApiKeyUsageLog", back_populates="api_key", cascade="all, delete-orphan"
    )


class ApiKeyUsageLog(Base):
    """Per-request usage log — one row per API call made with a key."""

    __tablename__ = "api_key_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. /v1/agents
    method: Mapped[str] = mapped_column(String(10), nullable=False)     # GET, POST…
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    request_bytes: Mapped[int] = mapped_column(Integer, default=0)      # body size in
    response_bytes: Mapped[int] = mapped_column(Integer, default=0)     # body size out
    estimated_tokens: Mapped[int] = mapped_column(Integer, default=0)   # response_bytes / 4
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)        # wall-clock ms
    called_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    api_key = relationship("ApiKey", back_populates="usage_logs")
