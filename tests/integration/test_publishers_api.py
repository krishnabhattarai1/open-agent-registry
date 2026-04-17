"""Integration tests for publisher endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_publisher(client: AsyncClient):
    resp = await client.post("/v1/publishers", json={
        "name": "Acme Corp",
        "slug": "acme-corp",
        "email": "admin@acme.com",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "acme-corp"
    assert "api_key" in data
    assert data["api_key"].startswith("oar_")


@pytest.mark.asyncio
async def test_get_publisher(client: AsyncClient):
    # Create first
    await client.post("/v1/publishers", json={
        "name": "Test Publisher",
        "slug": "test-pub",
        "email": "test@example.com",
    })
    resp = await client.get("/v1/publishers/test-pub")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "test-pub"


@pytest.mark.asyncio
async def test_get_publisher_not_found(client: AsyncClient):
    resp = await client.get("/v1/publishers/does-not-exist")
    assert resp.status_code == 404
