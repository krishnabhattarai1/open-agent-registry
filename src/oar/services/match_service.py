"""Core matching engine — the primary agent-facing discovery service.

Implements structured capability matching with server-side filtering
so agents receive compact, pre-filtered results rather than verbose
lists to parse themselves.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from oar.models.agent import Agent, AgentEndpoint, Capability
from oar.models.publisher import Publisher
from oar.schemas.match import CompactAgentResult, MatchQuery, MatchResponse
from oar.taxonomy import compute_match_score, match_all, match_any


async def match_agents(db: AsyncSession, query: MatchQuery) -> MatchResponse:
    """Run a structured capability match query.

    Filters agents server-side by need/proto/auth, scores by want,
    and returns compact results sorted by score descending.
    """
    # Build base query — active agents with their capabilities and endpoints
    stmt = (
        select(Agent)
        .where(Agent.status == "active")
        .options(
            selectinload(Agent.capabilities),
            selectinload(Agent.endpoints),
            selectinload(Agent.publisher),
        )
    )

    # Protocol filter in DB
    if query.proto:
        stmt = stmt.join(AgentEndpoint).where(AgentEndpoint.protocol == query.proto)

    result = await db.execute(stmt)
    candidates = list(result.scalars().unique().all())

    matched: list[tuple[Agent, int, str]] = []  # (agent, score, primary_endpoint_url)

    for agent in candidates:
        agent_codes = [cap.code for cap in agent.capabilities]

        # Must satisfy all `need` codes
        if not match_all(query.need, agent_codes):
            continue

        # Auth filter
        if query.auth:
            endpoints = agent.endpoints
            if query.proto:
                endpoints = [e for e in endpoints if e.protocol == query.proto]
            if not any(
                e.auth_type and e.auth_type in query.auth for e in endpoints
            ):
                continue

        # io_in filter — check if any capability accepts that input type
        if query.io_in:
            has_io = any(
                cap.input_types and query.io_in in cap.input_types
                for cap in agent.capabilities
            )
            if not has_io:
                continue

        score = compute_match_score(query.need, query.want, agent_codes)

        if score < query.min_score:
            continue

        # Primary endpoint URL (prefer requested protocol, else first)
        endpoints = agent.endpoints
        if query.proto:
            proto_eps = [e for e in endpoints if e.protocol == query.proto]
            primary_ep = proto_eps[0].url if proto_eps else (endpoints[0].url if endpoints else "")
        else:
            primary_ep = endpoints[0].url if endpoints else ""

        matched.append((agent, score, primary_ep))

    # Sort by score descending, limit
    matched.sort(key=lambda x: x[1], reverse=True)
    matched = matched[: query.limit]

    results = [
        CompactAgentResult(
            id=agent.short_id,
            n=agent.name,
            c=[cap.code for cap in agent.capabilities],
            p=query.proto or (agent.endpoints[0].protocol if agent.endpoints else "rest"),
            v=agent.version,
            s=score,
        )
        for agent, score, _ in matched
    ]

    import hashlib, json
    etag = hashlib.md5(
        json.dumps([r.model_dump() for r in results], sort_keys=True).encode()
    ).hexdigest()[:16]

    return MatchResponse(r=results, t=len(results), ttl=3600, **{"_etag": etag})
