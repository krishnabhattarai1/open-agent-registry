"""Unit tests for the compact serializer."""

from oar.compact import compact_agent_summary, compact_match_response, select_fields


def test_compact_agent_summary():
    result = compact_agent_summary("cr-01", "CodeOwl", ["code.review"], "a2a", "1.0", 95)
    assert result == {"id": "cr-01", "n": "CodeOwl", "c": ["code.review"], "p": "a2a", "v": "1.0", "s": 95}


def test_compact_match_response():
    results = [{"id": "cr-01", "n": "CodeOwl", "c": ["code.review"], "p": "a2a", "v": "1.0", "s": 95}]
    resp = compact_match_response(results, total=1, ttl=3600, etag="abc123")
    assert resp["r"] == results
    assert resp["t"] == 1
    assert resp["ttl"] == 3600
    assert resp["_etag"] == "abc123"


def test_select_fields_ep_auth():
    data = {
        "id": "cr-01",
        "endpoint": "https://agent.example.com",
        "auth": {"t": "bearer"},
        "protocol": "a2a",
        "description": "A code reviewer",
        "tags": ["python"],
    }
    result = select_fields(data, ["ep", "auth"])
    assert "endpoint" in result
    assert "auth" in result
    assert "id" in result
    assert "description" not in result
    assert "tags" not in result


def test_select_fields_always_includes_id():
    data = {"id": "cr-01", "endpoint": "https://example.com", "description": "test"}
    result = select_fields(data, ["ep"])
    assert "id" in result
