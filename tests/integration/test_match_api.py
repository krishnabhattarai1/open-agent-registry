"""Integration tests for the match endpoint — the critical discovery path."""

import pytest
from httpx import AsyncClient


async def _create_publisher_and_agent(client: AsyncClient, suffix: str = "") -> str:
    """Helper: create a publisher + agent, return API key."""
    pub_resp = await client.post("/v1/publishers", json={
        "name": f"Match Test Pub {suffix}",
        "slug": f"match-test-pub{suffix}",
        "email": f"test{suffix}@example.com",
    })
    api_key = pub_resp.json()["api_key"]

    await client.post(
        "/v1/agents",
        json={
            "name": f"Code Reviewer {suffix}",
            "slug": f"code-reviewer{suffix}",
            "description": "Reviews code for bugs and style issues",
            "version": "1.0.0",
            "capabilities": [
                {"code": "code.review", "input_types": ["text/plain"], "output_types": ["application/json"]},
                {"code": "code.fix"},
            ],
            "endpoints": [{"protocol": "a2a", "url": "https://example.com/a2a", "auth_type": "bearer"}],
            "tags": ["python"],
        },
        headers={"Authorization": f"Bearer {api_key}"},
    )
    return api_key


@pytest.mark.asyncio
async def test_match_basic(client: AsyncClient):
    await _create_publisher_and_agent(client, "-m1")

    resp = await client.post("/v1/match", json={
        "need": ["code.review"],
        "limit": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "r" in data
    assert "t" in data
    assert "ttl" in data
    assert data["ttl"] == 3600


@pytest.mark.asyncio
async def test_match_with_protocol_filter(client: AsyncClient):
    await _create_publisher_and_agent(client, "-m2")

    resp = await client.post("/v1/match", json={
        "need": ["code.review"],
        "proto": "a2a",
    })
    assert resp.status_code == 200
    results = resp.json()["r"]
    for r in results:
        assert r["p"] == "a2a"


@pytest.mark.asyncio
async def test_match_no_results(client: AsyncClient):
    resp = await client.post("/v1/match", json={
        "need": ["sec.pentest"],  # unlikely to exist in test DB
        "proto": "grpc",
    })
    assert resp.status_code == 200
    assert resp.json()["t"] == 0


@pytest.mark.asyncio
async def test_match_response_is_compact(client: AsyncClient):
    """Verify compact keys are returned (not verbose field names)."""
    await _create_publisher_and_agent(client, "-m3")

    resp = await client.post("/v1/match", json={"need": ["code.review"]})
    assert resp.status_code == 200
    results = resp.json()["r"]
    if results:
        # Compact keys: id, n, c, p, v, s
        r = results[0]
        assert "n" in r        # name (compact)
        assert "c" in r        # capabilities (compact)
        assert "p" in r        # protocol (compact)
        assert "s" in r        # score (compact)
        assert "name" not in r  # NOT verbose


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
