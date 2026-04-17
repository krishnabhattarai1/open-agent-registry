"""Multi-key support: api_keys and api_key_usage_logs tables.

Revision ID: 002
Revises: 001
Create Date: 2025-01-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── api_keys ──────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "publisher_id",
            UUID(as_uuid=True),
            sa.ForeignKey("publishers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_publisher_id", "api_keys", ["publisher_id"])
    op.create_index("ix_api_keys_status", "api_keys", ["status"])

    # ── api_key_usage_logs ────────────────────────────────────────────────────
    op.create_table(
        "api_key_usage_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "api_key_id",
            UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("status_code", sa.Integer, nullable=False),
        sa.Column("request_bytes", sa.Integer, server_default="0"),
        sa.Column("response_bytes", sa.Integer, server_default="0"),
        sa.Column("estimated_tokens", sa.Integer, server_default="0"),
        sa.Column("duration_ms", sa.Integer, server_default="0"),
        sa.Column("called_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_key_usage_logs_api_key_id", "api_key_usage_logs", ["api_key_id"])
    op.create_index("ix_api_key_usage_logs_called_at", "api_key_usage_logs", ["called_at"])

    # Migrate existing publisher keys → api_keys table (name = "default")
    op.execute("""
        INSERT INTO api_keys (id, publisher_id, name, key_hash, key_prefix, status, created_at)
        SELECT
            gen_random_uuid(),
            id,
            'default',
            api_key_hash,
            api_key_prefix,
            'active',
            created_at
        FROM publishers
        WHERE api_key_hash IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_table("api_key_usage_logs")
    op.drop_table("api_keys")
