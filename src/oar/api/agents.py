"""Agent CRUD + field-selective fetch endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from oar.compact import select_fields
from oar.dependencies import get_current_publisher, get_db
from oar.models.publisher import Publisher
from oar.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    AgentVersionResponse,
)
from oar.services import agent_service

router = APIRouter(prefix="/v1/agents", tags=["agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    publisher: Publisher = Depends(get_current_publisher),
) -> AgentResponse:
    """Register a new agent under the authenticated publisher."""
    # Check for slug conflict
    existing = await agent_service.get_agent_by_publisher_slug(db, publisher.slug, data.slug)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent slug already exists")

    agent = await agent_service.create_agent(db, publisher, data)
    return AgentResponse.from_orm_agent(agent)


@router.get("", response_model=AgentListResponse)
async def list_agents(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None, description="Text search"),
    publisher: str | None = Query(None),
    protocol: str | None = Query(None),
    tag: str | None = Query(None),
    status: str = Query("active"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> AgentListResponse:
    agents, total = await agent_service.list_agents(
        db, status=status, publisher_slug=publisher,
        protocol=protocol, tag=tag, q=q, page=page, per_page=per_page,
    )
    return AgentListResponse(
        data=[AgentResponse.from_orm_agent(a) for a in agents],
        meta={"page": page, "per_page": per_page, "total": total},
    )


@router.get("/{short_id}")
async def get_agent_by_id(
    short_id: str,
    fields: str | None = Query(None, description="Comma-separated field groups: ep,auth,caps,proto,meta,desc"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get agent by short_id. Use ?fields=ep,auth for compact connection info."""
    agent = await agent_service.get_agent_by_short_id(db, short_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        # Build full dict then filter
        full = _agent_to_dict(agent)
        return select_fields(full, field_list)

    return AgentResponse.from_orm_agent(agent)


@router.get("/{publisher_slug}/{agent_slug}", response_model=AgentResponse)
async def get_agent(
    publisher_slug: str,
    agent_slug: str,
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    """Get full agent card by publisher/agent slug (human-readable URL)."""
    agent = await agent_service.get_agent_by_publisher_slug(db, publisher_slug, agent_slug)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.from_orm_agent(agent)


@router.patch("/{publisher_slug}/{agent_slug}", response_model=AgentResponse)
async def update_agent(
    publisher_slug: str,
    agent_slug: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_publisher: Publisher = Depends(get_current_publisher),
) -> AgentResponse:
    agent = await agent_service.get_agent_by_publisher_slug(db, publisher_slug, agent_slug)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if str(agent.publisher_id) != str(current_publisher.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your agent")
    updated = await agent_service.update_agent(db, agent, data)
    return AgentResponse.from_orm_agent(updated)


@router.delete("/{publisher_slug}/{agent_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_agent(
    publisher_slug: str,
    agent_slug: str,
    db: AsyncSession = Depends(get_db),
    current_publisher: Publisher = Depends(get_current_publisher),
) -> None:
    agent = await agent_service.get_agent_by_publisher_slug(db, publisher_slug, agent_slug)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if str(agent.publisher_id) != str(current_publisher.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your agent")
    await agent_service.archive_agent(db, agent)


@router.get("/{publisher_slug}/{agent_slug}/versions", response_model=list[AgentVersionResponse])
async def get_agent_versions(
    publisher_slug: str,
    agent_slug: str,
    db: AsyncSession = Depends(get_db),
) -> list[AgentVersionResponse]:
    agent = await agent_service.get_agent_by_publisher_slug(db, publisher_slug, agent_slug)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    versions = await agent_service.get_agent_versions(db, agent.id)
    return [AgentVersionResponse.model_validate(v) for v in versions]


def _agent_to_dict(agent: Any) -> dict[str, Any]:
    """Convert agent ORM object to dict for field selection."""
    eps = agent.endpoints
    primary_ep = eps[0].url if eps else None
    primary_auth_type = eps[0].auth_type if eps else None
    primary_auth_config = eps[0].auth_config if eps else None

    auth: dict[str, Any] | None = None
    if primary_auth_type:
        auth = {"t": primary_auth_type}
        if primary_auth_config:
            auth.update(primary_auth_config)

    return {
        "id": agent.short_id,
        "endpoint": primary_ep,
        "auth": auth,
        "protocol": eps[0].protocol if eps else None,
        "capabilities": [{"code": c.code, "in": c.input_types, "out": c.output_types} for c in agent.capabilities],
        "description": agent.description,
        "publisher": agent.publisher.slug,
        "tags": [t.name for t in agent.tags],
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }
