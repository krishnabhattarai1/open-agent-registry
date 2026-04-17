"""Agent CRUD business logic."""

import secrets
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oar.models.agent import Agent, AgentEndpoint, AgentVersion, Capability
from oar.models.publisher import Publisher
from oar.models.tag import Tag
from oar.schemas.agent import AgentCreate, AgentUpdate


def _generate_short_id() -> str:
    """Generate an 8-char base32 short ID."""
    return secrets.token_hex(4)


async def _get_or_create_tag(db: AsyncSession, name: str) -> Tag:
    name = name.lower().strip()
    result = await db.execute(select(Tag).where(Tag.name == name))
    tag = result.scalar_one_or_none()
    if not tag:
        tag = Tag(name=name)
        db.add(tag)
        await db.flush()
    return tag


async def create_agent(
    db: AsyncSession, publisher: Publisher, data: AgentCreate
) -> Agent:
    """Create an agent with all related records in one transaction."""
    # Ensure short_id is unique
    for _ in range(5):
        short_id = _generate_short_id()
        existing = await db.execute(select(Agent).where(Agent.short_id == short_id))
        if not existing.scalar_one_or_none():
            break

    agent = Agent(
        short_id=short_id,
        name=data.name,
        slug=data.slug,
        publisher_id=publisher.id,
        description=data.description,
        version=data.version,
        status=data.status,
        homepage_url=data.homepage_url,
        repository_url=data.repository_url,
        license=data.license,
    )
    db.add(agent)
    await db.flush()  # get agent.id

    # Capabilities
    for cap in data.capabilities:
        db.add(Capability(
            agent_id=agent.id,
            code=cap.code,
            input_types=cap.input_types,
            output_types=cap.output_types,
        ))

    # Endpoints
    for ep in data.endpoints:
        db.add(AgentEndpoint(
            agent_id=agent.id,
            protocol=ep.protocol,
            url=str(ep.url),
            auth_type=ep.auth_type,
            auth_config=ep.auth_config,
            metadata_=ep.metadata,
        ))

    # Tags
    for tag_name in data.tags:
        tag = await _get_or_create_tag(db, tag_name)
        agent.tags.append(tag)

    # Initial version snapshot
    db.add(AgentVersion(
        agent_id=agent.id,
        version=data.version,
        manifest_snapshot=data.model_dump(),
    ))

    await db.commit()
    await db.refresh(agent)
    return agent


async def get_agent_by_short_id(db: AsyncSession, short_id: str) -> Agent | None:
    result = await db.execute(
        select(Agent)
        .where(Agent.short_id == short_id)
        .options(
            selectinload(Agent.capabilities),
            selectinload(Agent.endpoints),
            selectinload(Agent.tags),
            selectinload(Agent.publisher),
        )
    )
    return result.scalar_one_or_none()


async def get_agent_by_publisher_slug(
    db: AsyncSession, publisher_slug: str, agent_slug: str
) -> Agent | None:
    result = await db.execute(
        select(Agent)
        .join(Publisher)
        .where(Publisher.slug == publisher_slug, Agent.slug == agent_slug)
        .options(
            selectinload(Agent.capabilities),
            selectinload(Agent.endpoints),
            selectinload(Agent.tags),
            selectinload(Agent.publisher),
        )
    )
    return result.scalar_one_or_none()


async def list_agents(
    db: AsyncSession,
    status: str = "active",
    publisher_slug: str | None = None,
    protocol: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Agent], int]:
    """List agents with filters. Returns (agents, total_count)."""
    from oar.models.tag import agent_tags as agent_tags_table

    stmt = (
        select(Agent)
        .join(Publisher)
        .options(
            selectinload(Agent.capabilities),
            selectinload(Agent.endpoints),
            selectinload(Agent.tags),
            selectinload(Agent.publisher),
        )
    )

    if status:
        stmt = stmt.where(Agent.status == status)
    if publisher_slug:
        stmt = stmt.where(Publisher.slug == publisher_slug)
    if protocol:
        stmt = stmt.join(AgentEndpoint).where(AgentEndpoint.protocol == protocol)
    if tag:
        stmt = (
            stmt.join(agent_tags_table, agent_tags_table.c.agent_id == Agent.id)
            .join(Tag, Tag.id == agent_tags_table.c.tag_id)
            .where(Tag.name == tag.lower())
        )
    if q:
        stmt = stmt.where(Agent.description.ilike(f"%{q}%"))

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginate
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def update_agent(
    db: AsyncSession, agent: Agent, data: AgentUpdate
) -> Agent:
    """Update agent fields. Creates a new version snapshot if version changes."""
    version_changed = data.version and data.version != agent.version

    for field in ["name", "description", "version", "status", "homepage_url", "repository_url", "license"]:
        value = getattr(data, field)
        if value is not None:
            setattr(agent, field, value)

    if data.capabilities is not None:
        for cap in agent.capabilities:
            await db.delete(cap)
        for cap in data.capabilities:
            db.add(Capability(
                agent_id=agent.id,
                code=cap.code,
                input_types=cap.input_types,
                output_types=cap.output_types,
            ))

    if data.endpoints is not None:
        for ep in agent.endpoints:
            await db.delete(ep)
        for ep in data.endpoints:
            db.add(AgentEndpoint(
                agent_id=agent.id,
                protocol=ep.protocol,
                url=str(ep.url),
                auth_type=ep.auth_type,
                auth_config=ep.auth_config,
                metadata_=ep.metadata,
            ))

    if data.tags is not None:
        agent.tags.clear()
        for tag_name in data.tags:
            tag = await _get_or_create_tag(db, tag_name)
            agent.tags.append(tag)

    if version_changed:
        db.add(AgentVersion(
            agent_id=agent.id,
            version=data.version,
            manifest_snapshot=data.model_dump(exclude_none=True),
        ))

    await db.commit()
    await db.refresh(agent)
    return agent


async def archive_agent(db: AsyncSession, agent: Agent) -> None:
    agent.status = "archived"
    await db.commit()


async def get_agent_versions(db: AsyncSession, agent_id: uuid.UUID) -> list[AgentVersion]:
    result = await db.execute(
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.created_at.desc())
    )
    return list(result.scalars().all())
