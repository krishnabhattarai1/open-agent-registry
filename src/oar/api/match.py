"""POST /v1/match — the primary agent-facing discovery endpoint.

Accepts structured capability queries, returns compact results.
This is the main token-efficient entry point for agent-to-agent discovery.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from oar.dependencies import get_db
from oar.schemas.match import BatchFetchRequest, MatchQuery, MatchResponse
from oar.services import match_service
from oar.services import agent_service

router = APIRouter(prefix="/v1", tags=["discovery"])


@router.post("/match", response_model=MatchResponse)
async def match_agents(
    query: MatchQuery,
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    """Structured capability matching — the primary discovery endpoint.

    Accepts a capability query and returns compact, pre-filtered, scored results.

    Example (Agent A looking for a code reviewer via A2A):
        POST /v1/match
        {"need": ["code.review"], "proto": "a2a", "limit": 3}

    Response (~60 tokens):
        {"r": [{"id": "cr-01", "n": "CodeOwl", "c": ["code.review"], "p": "a2a", "s": 95}],
         "t": 1, "ttl": 3600}
    """
    return await match_service.match_agents(db, query)


@router.post("/agents/batch")
async def batch_fetch_agents(
    req: BatchFetchRequest,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Fetch multiple agents by short_id with optional field selection.

    Reduces round trips when an agent needs info on multiple candidates.

    Example:
        POST /v1/agents/batch
        {"ids": ["cr-01", "cr-02"], "fields": ["ep", "auth"]}
    """
    from oar.compact import select_fields
    from oar.api.agents import _agent_to_dict

    results = []
    for short_id in req.ids:
        agent = await agent_service.get_agent_by_short_id(db, short_id)
        if agent:
            data = _agent_to_dict(agent)
            if req.fields:
                data = select_fields(data, req.fields)
            results.append(data)
    return results
