"""Example: Agent-to-agent discovery flow using the OAR API.

Shows how an orchestrator agent discovers a code reviewer in ~100 tokens.

Stage 1: POST /v1/match  → compact results (~60 tokens)
Stage 2: GET /v1/agents/{id}?fields=ep,auth → connection info (~35 tokens)
Stage 3: Connect directly to the discovered agent (registry not involved)
"""

import httpx

REGISTRY = "http://localhost:8000"


def discover_and_connect():
    with httpx.Client(base_url=REGISTRY) as client:

        # ── Stage 1: Match (~60 tokens in response) ──────────────────────
        print("Stage 1: Finding a code reviewer via A2A...")
        match_resp = client.post("/v1/match", json={
            "need": ["code.review"],
            "proto": "a2a",
            "limit": 3,
        })
        match_resp.raise_for_status()
        match_data = match_resp.json()

        print(f"Response (~{len(str(match_data))} chars):")
        print(match_data)
        # Example: {"r": [{"id": "cr-01", "n": "CodeOwl", "c": ["code.review"],
        #                   "p": "a2a", "v": "1.0", "s": 95}], "t": 1, "ttl": 3600}

        if not match_data["r"]:
            print("No agents found.")
            return

        # Pick the highest-scored result (already sorted)
        best = match_data["r"][0]
        agent_id = best["id"]
        print(f"\nSelected: {best['n']} (score={best['s']})")

        # ── Stage 2: Get connection info only (~35 tokens) ────────────────
        print(f"\nStage 2: Fetching connection info for {agent_id}...")
        info_resp = client.get(f"/v1/agents/{agent_id}", params={"fields": "ep,auth"})
        info_resp.raise_for_status()
        connect_info = info_resp.json()

        print(f"Response (~{len(str(connect_info))} chars):")
        print(connect_info)
        # Example: {"id": "cr-01", "endpoint": "https://codeowl.ai/a2a",
        #           "auth": {"t": "bearer"}}

        endpoint_url = connect_info.get("endpoint")
        auth_info = connect_info.get("auth")

        # ── Stage 3: Direct connection (registry not involved) ────────────
        print(f"\nStage 3: Connecting directly to {endpoint_url}")
        print("(Registry is done — all further communication is agent-to-agent)")

        # In real usage, you would use the A2A/MCP SDK here, e.g.:
        # a2a_client.send_task(endpoint_url, auth=auth_info, task={...})
        print("→ Would connect to agent via A2A protocol")

        total_chars = len(str(match_data)) + len(str(connect_info))
        print(f"\nTotal registry interaction: ~{total_chars} chars / ~{total_chars // 4} tokens")
        print("(vs ~900 tokens with verbose API design)")


if __name__ == "__main__":
    discover_and_connect()
