"""Compact serialization for token-efficient agent-to-agent responses.

Short key mapping (spec-level contract):
    id=identifier  n=name  c=capabilities  p=protocol  v=version
    s=score  ep=endpoint  d=description  t=total  r=results
    ttl=cache_seconds  m=metadata  io=input_output
"""

from typing import Any

# Verbose -> Compact key mapping
KEY_MAP: dict[str, str] = {
    "identifier": "id",
    "name": "n",
    "capabilities": "c",
    "protocol": "p",
    "version": "v",
    "score": "s",
    "endpoint": "ep",
    "description": "d",
    "total": "t",
    "results": "r",
    "cache_seconds": "ttl",
    "metadata": "m",
    "input_output": "io",
    "auth": "auth",
    "type": "t",
}

# Compact -> Verbose (reverse)
REVERSE_KEY_MAP: dict[str, str] = {v: k for k, v in KEY_MAP.items()}

# Field groups that can be requested via ?fields=
FIELD_GROUPS: dict[str, list[str]] = {
    "ep": ["endpoint"],
    "auth": ["auth"],
    "caps": ["capabilities"],
    "proto": ["protocol"],
    "meta": ["publisher", "created_at", "updated_at", "tags"],
    "desc": ["description", "long_description"],
    "io": ["input_output"],
}


def compact_agent_summary(
    agent_id: str,
    name: str,
    capabilities: list[str],
    protocol: str,
    version: str,
    score: int,
) -> dict[str, Any]:
    """Create a compact agent summary for search/match results."""
    return {
        "id": agent_id,
        "n": name,
        "c": capabilities,
        "p": protocol,
        "v": version,
        "s": score,
    }


def compact_connect_info(
    agent_id: str,
    endpoint_url: str,
    auth_type: str | None,
    auth_config: dict | None,
) -> dict[str, Any]:
    """Create minimal connection info for Stage 2 fetch."""
    result: dict[str, Any] = {"id": agent_id, "ep": endpoint_url}
    if auth_type:
        auth: dict[str, Any] = {"t": auth_type}
        if auth_config:
            auth.update(auth_config)
        result["auth"] = auth
    return result


def compact_match_response(
    results: list[dict[str, Any]],
    total: int,
    ttl: int = 3600,
    etag: str | None = None,
) -> dict[str, Any]:
    """Wrap match results in compact envelope."""
    resp: dict[str, Any] = {"r": results, "t": total, "ttl": ttl}
    if etag:
        resp["_etag"] = etag
    return resp


def select_fields(agent_data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Filter agent data to only include requested field groups.

    `fields` is a list of field group keys (e.g., ["ep", "auth", "caps"]).
    Always includes "id".
    """
    allowed_keys: set[str] = {"id", "short_id"}
    for field in fields:
        if field in FIELD_GROUPS:
            allowed_keys.update(FIELD_GROUPS[field])
        else:
            allowed_keys.add(field)
    return {k: v for k, v in agent_data.items() if k in allowed_keys}


def verbose_to_compact(data: dict[str, Any]) -> dict[str, Any]:
    """Convert verbose-keyed dict to compact keys."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        compact_key = KEY_MAP.get(key, key)
        result[compact_key] = value
    return result
