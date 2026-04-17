"""Initial schema — all MVP tables.

Revision ID: 001
Revises: None
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm for text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Publishers
    op.create_table(
        "publishers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("url", sa.String(512)),
        sa.Column("api_key_hash", sa.String(255), nullable=False),
        sa.Column("api_key_prefix", sa.String(8), nullable=False),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_publishers_slug", "publishers", ["slug"])
    op.create_index("ix_publishers_api_key_prefix", "publishers", ["api_key_prefix"])

    # Agents
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("short_id", sa.String(8), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("publisher_id", UUID(as_uuid=True), sa.ForeignKey("publishers.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("homepage_url", sa.String(512)),
        sa.Column("repository_url", sa.String(512)),
        sa.Column("license", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("publisher_id", "slug", name="uq_agent_publisher_slug"),
    )
    op.create_index("ix_agents_short_id", "agents", ["short_id"])
    op.create_index("ix_agents_slug", "agents", ["slug"])
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_agents_created_at", "agents", ["created_at"])
    # Trigram index for text search on description
    op.execute(
        "CREATE INDEX ix_agents_description_trgm ON agents USING gin (description gin_trgm_ops)"
    )

    # Agent versions
    op.create_table(
        "agent_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("manifest_snapshot", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("agent_id", "version", name="uq_agent_version"),
    )

    # Capabilities
    op.create_table(
        "capabilities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("input_types", sa.ARRAY(sa.Text())),
        sa.Column("output_types", sa.ARRAY(sa.Text())),
    )
    op.create_index("ix_capabilities_code", "capabilities", ["code"])
    op.create_index("ix_capabilities_agent_id", "capabilities", ["agent_id"])

    # Agent endpoints
    op.create_table(
        "agent_endpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("protocol", sa.String(50), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("auth_type", sa.String(50)),
        sa.Column("auth_config", JSONB),
        sa.Column("metadata", JSONB),
    )
    op.create_index("ix_agent_endpoints_protocol", "agent_endpoints", ["protocol"])
    op.create_index("ix_agent_endpoints_agent_id", "agent_endpoints", ["agent_id"])

    # Tags
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )
    op.create_index("ix_tags_name", "tags", ["name"])

    # Agent-tag association
    op.create_table(
        "agent_tags",
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("agent_tags")
    op.drop_table("tags")
    op.drop_table("agent_endpoints")
    op.drop_table("capabilities")
    op.drop_table("agent_versions")
    op.drop_table("agents")
    op.drop_table("publishers")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
