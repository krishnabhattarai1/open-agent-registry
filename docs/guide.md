# Open Agent Registry — Complete Guide

## Table of Contents

1. [What is OAR?](#what-is-oar)
2. [Getting Started](#getting-started)
3. [Authentication](#authentication)
4. [Publisher Registration](#publisher-registration)
5. [Agent Registration](#agent-registration)
6. [Agent Cards — the Manifest Format](#agent-cards--the-manifest-format)
7. [Capability Taxonomy](#capability-taxonomy)
8. [Discovery — Finding Agents](#discovery--finding-agents)
9. [Two-Stage Discovery Protocol](#two-stage-discovery-protocol)
10. [Updating and Managing Agents](#updating-and-managing-agents)
11. [CLI Reference](#cli-reference)
12. [API Reference](#api-reference)
13. [Agent-to-Agent Integration Examples](#agent-to-agent-integration-examples)
14. [Token Budget Guide](#token-budget-guide)

---

## What is OAR?

Open Agent Registry (OAR) is a centralized registry where AI agents publish their capabilities and discover one another. It is designed for **agent-to-agent communication**, meaning the primary consumers are other LLMs — not humans. Every design decision prioritises minimising the tokens an agent must process to complete a discovery flow.

**What OAR is:**
- A directory where agents publish what they can do (capabilities), how to reach them (endpoints), and how to authenticate
- A broker that connects agents and then gets out of the way
- A token-efficient protocol: a full discovery cycle costs ~100 tokens vs ~900 in a verbose design

**What OAR is not:**
- A message proxy — once two agents know each other's endpoints, OAR plays no further role
- An orchestrator — it does not coordinate multi-agent tasks
- A monitoring service — it does not track agent health or uptime

---

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.12+
- `pip`

### 1. Start the registry

```bash
git clone https://github.com/your-org/open-agent-registry
cd open-agent-registry

docker compose up -d        # starts PostgreSQL on port 5432
pip install -e ".[dev]"     # installs the oar package and CLI
alembic upgrade head        # creates all database tables
uvicorn oar.main:app --reload --port 8000
```

The API is now running at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### 2. Configure the CLI

```bash
oar config set registry-url http://localhost:8000
```

### 3. Verify it's running

```bash
curl http://localhost:8000/health
# → {"status": "ok"}

curl http://localhost:8000/v1/status
# → {"status": "ok", "version": "0.1.0"}
```

### 4. Complete walkthrough in 5 minutes

```bash
# Step 1: Register as a publisher
curl -s -X POST http://localhost:8000/v1/publishers \
  -H "Content-Type: application/json" \
  -d '{"name":"Acme AI","slug":"acme-ai","email":"admin@acme.ai"}' | jq .
# Save the api_key from the response — shown once only

# Step 2: Configure your key
oar config set api-key oar_YOUR_KEY_HERE

# Step 3: Validate and register your agent
oar validate examples/agent-card.yaml
oar register examples/agent-card.yaml

# Step 4: Discover agents (as another agent would)
oar match --need code.review --proto a2a

# Step 5: Get connection info
oar info SHORT_ID --fields ep,auth
```

---

## Authentication

OAR uses **API keys** for write operations. Read operations (discovery, listing, viewing agents) are public — no key needed.

### Key format

All API keys use the prefix `oar_` followed by 32 hex characters:

```
oar_3f9a2b1c4d5e6f7a8b9c0d1e2f3a4b5c
```

### Passing your key

Include the key in every write request as a Bearer token:

```http
Authorization: Bearer oar_3f9a2b1c4d5e6f7a8b9c0d1e2f3a4b5c
```

### What requires a key

| Operation | Auth required |
|---|---|
| Register a publisher | No |
| Register an agent | **Yes** |
| Update an agent | **Yes (owner only)** |
| Delete/archive an agent | **Yes (owner only)** |
| Discover agents (`POST /v1/match`) | No |
| List or view agents | No |
| Browse the taxonomy | No |

### Key security

- Your key is shown **exactly once** at publisher registration. Store it immediately.
- Keys cannot be retrieved after creation. If lost, contact the registry operator to rotate.
- Never include your key in agent card files or public repositories.
- The registry stores only a bcrypt hash — the raw key is never persisted.

---

## Publisher Registration

A **publisher** is the entity (person, team, or organisation) that owns and maintains agents. You register once and then use your API key to manage any number of agents under your publisher slug.

### Register via API

```bash
curl -X POST http://localhost:8000/v1/publishers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme AI",
    "slug": "acme-ai",
    "email": "admin@acme.ai",
    "url": "https://acme.ai"
  }'
```

**Response (201 Created):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme AI",
  "slug": "acme-ai",
  "email": "admin@acme.ai",
  "url": "https://acme.ai",
  "verified": false,
  "created_at": "2025-01-15T10:30:00Z",
  "api_key": "oar_3f9a2b1c4d5e6f7a8b9c0d1e2f3a4b5c"
}
```

> **Important:** Copy `api_key` now. It will not appear again.

### Publisher slug rules

- Lowercase letters, numbers, and hyphens only
- Must start with a letter or number
- Examples: `acme-ai`, `research-lab-mit`, `johndoe`

### Look up a publisher

```bash
curl http://localhost:8000/v1/publishers/acme-ai
```

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme AI",
  "slug": "acme-ai",
  "verified": false,
  "created_at": "2025-01-15T10:30:00Z"
}
```

---

## Agent Registration

An **agent** is a single AI service with a defined set of capabilities and one or more protocol endpoints. Agents are namespaced under their publisher: `acme-ai/code-reviewer`.

### Method 1 — via CLI (recommended)

Write an `agent-card.yaml` file (see [Agent Cards](#agent-cards--the-manifest-format) below), then:

```bash
# Validate locally first (no network call)
oar validate agent-card.yaml

# Register (creates new agent)
oar register agent-card.yaml

# Or publish (create if new, update if exists)
oar publish agent-card.yaml
```

### Method 2 — via API

```bash
curl -X POST http://localhost:8000/v1/agents \
  -H "Authorization: Bearer oar_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Code Reviewer",
    "slug": "code-reviewer",
    "description": "Reviews pull requests for bugs, security issues, and style",
    "version": "1.0.0",
    "capabilities": [
      {
        "code": "code.review",
        "input_types": ["text/plain", "text/x-diff"],
        "output_types": ["application/json"]
      },
      {
        "code": "code.fix",
        "input_types": ["text/plain"],
        "output_types": ["text/plain"]
      }
    ],
    "endpoints": [
      {
        "protocol": "a2a",
        "url": "https://code-reviewer.acme.ai/.well-known/agent.json",
        "auth_type": "bearer",
        "auth_config": {
          "token_url": "https://auth.acme.ai/token"
        }
      },
      {
        "protocol": "mcp",
        "url": "https://code-reviewer.acme.ai/mcp",
        "auth_type": "api_key"
      }
    ],
    "tags": ["python", "javascript", "security"],
    "license": "Apache-2.0",
    "homepage_url": "https://github.com/acme/code-reviewer",
    "repository_url": "https://github.com/acme/code-reviewer"
  }'
```

**Response (201 Created):**

```json
{
  "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "short_id": "3f9a2b1c",
  "name": "Code Reviewer",
  "slug": "code-reviewer",
  "publisher": {
    "slug": "acme-ai",
    "name": "Acme AI",
    "verified": false
  },
  "description": "Reviews pull requests for bugs, security issues, and style",
  "version": "1.0.0",
  "status": "active",
  "capabilities": [
    {"code": "code.review", "input_types": ["text/plain", "text/x-diff"], "output_types": ["application/json"]},
    {"code": "code.fix", "input_types": ["text/plain"], "output_types": ["text/plain"]}
  ],
  "endpoints": [
    {"protocol": "a2a", "url": "https://code-reviewer.acme.ai/.well-known/agent.json", "auth_type": "bearer"},
    {"protocol": "mcp", "url": "https://code-reviewer.acme.ai/mcp", "auth_type": "api_key"}
  ],
  "tags": ["python", "javascript", "security"],
  "created_at": "2025-01-15T10:35:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

Note the `short_id` field (`3f9a2b1c`) — this 8-character ID is what other agents use in compact discovery responses and for direct lookups.

### Agent slug rules

Same as publisher slugs: lowercase, numbers, hyphens, starts with letter or number. The combination of `publisher_slug/agent_slug` must be globally unique.

---

## Agent Cards — the Manifest Format

An **agent card** (`agent-card.yaml`) is the file your team maintains alongside your agent's source code. It is the single source of truth for what the agent can do and how to reach it.

### Full example

```yaml
# agent-card.yaml
oar: "1.0"                              # manifest format version

name: "code-reviewer"
description: "Reviews pull requests for bugs, security issues, and code style"
version: "1.2.0"                        # semver
publisher: "acme-ai"                    # must match your registered publisher slug

homepage: "https://github.com/acme/code-reviewer"
repository: "https://github.com/acme/code-reviewer"
license: "Apache-2.0"                   # SPDX identifier
status: "active"                        # active | deprecated | archived

tags:
  - python
  - javascript
  - security
  - code-quality

capabilities:
  - code: "code.review"                 # taxonomy code — required
    input_types:                        # MIME types you accept
      - "text/plain"
      - "text/x-diff"
    output_types:                       # MIME types you return
      - "application/json"
  - code: "code.fix"
    input_types: ["text/plain"]
    output_types: ["text/plain"]
  - code: "sec.scan"
    input_types: ["text/plain"]
    output_types: ["application/json"]

endpoints:
  - protocol: "a2a"                     # a2a | mcp | acp | rest | grpc
    url: "https://code-reviewer.acme.ai/.well-known/agent.json"
    auth:
      type: "bearer"                    # bearer | api_key | oauth2 | none
      config:
        token_url: "https://auth.acme.ai/token"
        scopes: ["review:read", "review:write"]

  - protocol: "mcp"
    url: "https://code-reviewer.acme.ai/mcp"
    auth:
      type: "api_key"

  - protocol: "rest"
    url: "https://code-reviewer.acme.ai/api/v1"
    auth:
      type: "none"
```

### Field reference

| Field | Required | Description |
|---|---|---|
| `oar` | Yes | Manifest format version. Use `"1.0"`. |
| `name` | Yes | Human-readable name. Max 255 chars. |
| `description` | Yes | What this agent does. Keep it precise — it is used for text search. |
| `version` | Yes | Semver string: `MAJOR.MINOR.PATCH`. |
| `publisher` | Yes | Your publisher slug (e.g. `acme-ai`). |
| `status` | No | `active` (default), `deprecated`, or `archived`. |
| `homepage` | No | Project homepage URL. |
| `repository` | No | Source code URL. |
| `license` | No | SPDX license identifier (e.g. `MIT`, `Apache-2.0`). |
| `tags` | No | Free-form tags for filtering. Lowercase recommended. |
| `capabilities` | No | List of capability objects (see below). |
| `endpoints` | No | List of endpoint objects (see below). |

### Capability object

```yaml
capabilities:
  - code: "code.review"          # Required — must be a valid taxonomy code
    input_types:                 # Optional — MIME types you accept as input
      - "text/plain"
    output_types:                # Optional — MIME types you return
      - "application/json"
```

Run `oar taxonomy` to see all valid codes.

### Endpoint object

```yaml
endpoints:
  - protocol: "a2a"              # Required — a2a | mcp | acp | rest | grpc
    url: "https://..."           # Required — your agent's URL for this protocol
    auth:
      type: "bearer"             # Required if auth present — bearer | api_key | oauth2 | none
      config:                    # Optional — protocol-specific auth details
        token_url: "..."
```

### Validate before registering

The CLI validates your manifest locally against the full schema, including taxonomy code checks, before making any network call:

```bash
oar validate agent-card.yaml
# ✓ agent-card.yaml is valid

# Example error output:
# Validation errors in agent-card.yaml:
#   capabilities → 0 → code: Unknown capability code: 'code.analyse'.
#                       Run `oar taxonomy` for valid codes.
```

---

## Capability Taxonomy

The taxonomy is the foundation of token-efficient discovery. Instead of agents parsing verbose natural language descriptions, they match on structured codes.

### Format

Codes follow a `domain.action` or `domain.action.qualifier` hierarchy:

```
code.review        →  domain=code, action=review
web.api.call       →  domain=web, action=api, qualifier=call
media.img.gen      →  domain=media, action=img, qualifier=gen
```

### All built-in codes

| Domain | Codes |
|---|---|
| `code` | `review` `gen` `fix` `lint` `test` `refactor` `doc` `translate` `explain` `debug` |
| `data` | `transform` `validate` `enrich` `clean` `dedupe` `merge` `aggregate` `parse` `convert` |
| `text` | `summarize` `translate` `classify` `extract` `generate` `edit` `sentiment` `embed` `qa` |
| `web` | `scrape` `browse` `monitor` `screenshot` `api.call` `crawl` |
| `search` | `semantic` `keyword` `rag` `vector` `index` |
| `reason` | `plan` `math` `decide` `decompose` `verify` |
| `media` | `img.gen` `img.edit` `img.describe` `audio.transcribe` `audio.gen` `video.summarize` |
| `file` | `read` `write` `convert` `compress` `parse` |
| `db` | `query` `migrate` `model` `optimize` |
| `sec` | `scan` `audit` `pentest` `monitor` |
| `infra` | `deploy` `provision` `monitor` `scale` `backup` |
| `comms` | `email.send` `email.read` `chat.send` `notify` |

### Browse via CLI or API

```bash
oar taxonomy            # show all domains and codes
oar taxonomy code       # show only code.* codes
```

```bash
curl http://localhost:8000/v1/taxonomy
```

```json
{
  "v": 1,
  "domains": {
    "code": ["review", "gen", "fix", "lint", "test", "refactor", "doc", "translate", "explain", "debug"],
    "data": ["transform", "validate", "enrich", ...],
    ...
  }
}
```

The taxonomy is versioned. Cache the response aggressively — it changes rarely. The response includes `Cache-Control: public, max-age=604800` (7 days).

### Matching rules

When you run a discovery query, these rules determine which agents match:

| Rule | Query | Matches |
|---|---|---|
| **Exact** | `"code.review"` | Only agents with exactly `code.review` |
| **Prefix** | `"code"` | Any agent with `code.*` (code.review, code.gen, code.fix…) |
| **All-of** | `["code.review", "code.fix"]` | Agents that have both |
| **Score boost** | `want: ["code.test"]` | Agents with `code.test` score 30 points higher |

---

## Discovery — Finding Agents

Discovery is optimised for agents consuming the results. All discovery endpoints return compact short-key JSON by default.

### The match endpoint (primary)

`POST /v1/match` is the recommended discovery method. You describe what you need; the server filters and scores agents; you receive only the relevant candidates.

```bash
curl -X POST http://localhost:8000/v1/match \
  -H "Content-Type: application/json" \
  -d '{
    "need": ["code.review"],
    "proto": "a2a",
    "limit": 3
  }'
```

```json
{
  "r": [
    {"id": "3f9a2b1c", "n": "Code Reviewer", "c": ["code.review", "code.fix"], "p": "a2a", "v": "1.2.0", "s": 95},
    {"id": "7e4c8d2f", "n": "LintBot",       "c": ["code.review", "code.lint"], "p": "a2a", "v": "2.0.1", "s": 87}
  ],
  "t": 2,
  "ttl": 3600,
  "_etag": "a1b2c3d4"
}
```

**Compact key legend:**

| Key | Meaning | Type |
|---|---|---|
| `r` | results array | array |
| `id` | agent short_id (8 chars) | string |
| `n` | name | string |
| `c` | capability codes | string[] |
| `p` | protocol | string |
| `v` | version | string |
| `s` | relevance score 0–100 | int |
| `t` | total matched | int |
| `ttl` | cache lifetime (seconds) | int |
| `_etag` | cache fingerprint | string |

### Full match query options

```json
{
  "need": ["code.review"],
  "want": ["code.fix", "sec.scan"],
  "proto": "a2a",
  "auth": ["bearer", "api_key"],
  "io_in": "text/x-diff",
  "limit": 5,
  "min_score": 70
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `need` | string[] | required | Capability codes that **must** all match |
| `want` | string[] | null | Preferred codes — boost score but not required |
| `proto` | string | null | Required protocol: `a2a`, `mcp`, `acp`, `rest`, `grpc` |
| `auth` | string[] | null | Acceptable auth types — agent must support at least one |
| `io_in` | string | null | MIME type the caller will send — filters by capability input_types |
| `limit` | int | 5 | Max results returned (1–50) |
| `min_score` | int | 0 | Minimum quality score to include in results (0–100) |

### Text / browse search

For human-readable browsing (not for agent-to-agent use — too verbose):

```bash
curl "http://localhost:8000/v1/agents?q=code+review&protocol=a2a&page=1&per_page=10"
```

```bash
oar search "code review" --proto a2a
oar search --tag python --tag security
oar list --publisher acme-ai --status active
```

---

## Two-Stage Discovery Protocol

This is the canonical flow for agent-to-agent discovery. Total registry interaction: 2 requests, ~100 tokens.

### Stage 1 — Match (~60 tokens)

Find candidates using structured query:

```http
POST /v1/match
Content-Type: application/json

{"need": ["code.review"], "proto": "a2a", "limit": 3}
```

Response — pick the highest `s` (score):

```json
{
  "r": [{"id": "3f9a2b1c", "n": "Code Reviewer", "c": ["code.review"], "p": "a2a", "s": 95}],
  "t": 1, "ttl": 3600
}
```

### Stage 2 — Connect Info (~35 tokens)

Fetch only the fields needed to establish a connection:

```http
GET /v1/agents/3f9a2b1c?fields=ep,auth
```

```json
{
  "id": "3f9a2b1c",
  "endpoint": "https://code-reviewer.acme.ai/.well-known/agent.json",
  "auth": {"t": "bearer", "url": "https://auth.acme.ai/token"}
}
```

### Stage 3 — Direct connection (registry done)

Use the endpoint URL and auth info to connect via A2A, MCP, or REST. The registry is no longer involved.

```python
# Example with A2A
import httpx

token = get_bearer_token("https://auth.acme.ai/token")
response = httpx.post(
    "https://code-reviewer.acme.ai/.well-known/agent.json",
    headers={"Authorization": f"Bearer {token}"},
    json={"task": "review", "diff": "..."}
)
```

### Field selection reference

Control exactly what fields you receive in Stage 2:

```http
GET /v1/agents/3f9a2b1c?fields=ep,auth,caps
```

| Field key | Returns |
|---|---|
| `ep` | endpoint URL |
| `auth` | auth type and config |
| `caps` | capability codes + I/O types |
| `proto` | protocol name |
| `meta` | publisher, timestamps, tags |
| `desc` | full description text |
| `io` | I/O constraints |

Combine multiple: `?fields=ep,auth,caps`

Always includes `id` regardless of field selection.

### Caching

OAR embeds cache metadata in every response body so agents behind SDKs or proxies always have access to it:

```json
{
  "r": [...],
  "ttl": 3600,
  "_etag": "a1b2c3d4"
}
```

On subsequent requests, pass the etag to get a 304 with empty body (zero tokens):

```http
GET /v1/agents/3f9a2b1c?fields=ep,auth
If-None-Match: "a1b2c3d4"

→ 304 Not Modified   (0 bytes in body)
```

Recommended TTLs for agent-side caching:

| Resource | TTL |
|---|---|
| Taxonomy | 7 days |
| Match results | 1 hour |
| Agent card (full) | 4 hours |
| Agent endpoint + auth | 4 hours |

### Batch fetch

When you need connection info for multiple agents at once (e.g. an orchestrator choosing between candidates):

```bash
curl -X POST http://localhost:8000/v1/agents/batch \
  -H "Content-Type: application/json" \
  -d '{
    "ids": ["3f9a2b1c", "7e4c8d2f"],
    "fields": ["ep", "auth", "proto"]
  }'
```

```json
[
  {"id": "3f9a2b1c", "endpoint": "https://code-reviewer.acme.ai/a2a", "auth": {"t": "bearer", ...}, "protocol": "a2a"},
  {"id": "7e4c8d2f", "endpoint": "https://lintbot.io/a2a", "auth": {"t": "api_key"}, "protocol": "a2a"}
]
```

---

## Updating and Managing Agents

### Update an agent

Send only the fields you want to change. If you change `version`, a new version snapshot is automatically recorded.

```bash
curl -X PATCH http://localhost:8000/v1/agents/acme-ai/code-reviewer \
  -H "Authorization: Bearer oar_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.3.0",
    "description": "Reviews pull requests with enhanced security scanning",
    "capabilities": [
      {"code": "code.review", "input_types": ["text/plain", "text/x-diff"], "output_types": ["application/json"]},
      {"code": "code.fix"},
      {"code": "sec.scan"},
      {"code": "sec.audit"}
    ]
  }'
```

Or via CLI:

```bash
# Edit agent-card.yaml (bump version, add capabilities), then:
oar publish agent-card.yaml
```

`oar publish` is idempotent — it creates the agent if it doesn't exist or updates it if it does.

### View version history

Every version is preserved as an immutable snapshot:

```bash
curl http://localhost:8000/v1/agents/acme-ai/code-reviewer/versions
```

```json
[
  {"version": "1.3.0", "created_at": "2025-02-01T09:00:00Z", "manifest_snapshot": {...}},
  {"version": "1.2.0", "created_at": "2025-01-15T10:35:00Z", "manifest_snapshot": {...}},
  {"version": "1.0.0", "created_at": "2025-01-10T08:00:00Z", "manifest_snapshot": {...}}
]
```

### Deprecate or archive an agent

**Deprecate** — still discoverable, but signals it should be replaced:

```bash
curl -X PATCH http://localhost:8000/v1/agents/acme-ai/code-reviewer \
  -H "Authorization: Bearer oar_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "deprecated"}'
```

**Archive** — removed from discovery results:

```bash
curl -X DELETE http://localhost:8000/v1/agents/acme-ai/code-reviewer \
  -H "Authorization: Bearer oar_YOUR_KEY"
# Sets status to "archived". Data is preserved — not physically deleted.
```

### View your agents

```bash
oar list --publisher acme-ai

# Full card
oar info acme-ai/code-reviewer

# Compact connection info
oar info 3f9a2b1c --fields ep,auth
```

---

## CLI Reference

Install: `pip install -e .` — installs the `oar` command.

### Configuration

```bash
oar config set registry-url http://localhost:8000
oar config set api-key oar_YOUR_KEY
oar config show
```

Config is stored at `~/.config/oar/config.toml`.

### Agent lifecycle

```bash
oar validate agent-card.yaml       # validate manifest locally (no network)
oar register agent-card.yaml       # create a new agent
oar publish agent-card.yaml        # create or update (idempotent)
```

### Discovery

```bash
# Structured match (agent-optimized, compact output)
oar match --need code.review
oar match --need code.review --need code.fix --proto a2a
oar match --need text.summarize --want text.translate --min-score 80
oar match --need code.review --proto a2a --json   # raw compact JSON

# Text search (human-readable)
oar search "code review"
oar search --tag python --proto a2a
oar search --cap code.review --publisher acme-ai
```

### Viewing agents

```bash
oar list                                     # all active agents
oar list --publisher acme-ai
oar list --proto mcp --status active
oar list --tag security

oar info acme-ai/code-reviewer               # full verbose card
oar info 3f9a2b1c                            # by short_id (compact)
oar info 3f9a2b1c --fields ep,auth           # connection info only
oar info acme-ai/code-reviewer --json        # raw JSON
```

### Taxonomy

```bash
oar taxonomy             # all domains and codes
oar taxonomy code        # only code.* codes
oar taxonomy text        # only text.* codes
```

---

## API Reference

Base URL: `http://your-registry/`

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/v1/status` | Version and status |

### Publishers

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/v1/publishers` | None | Register a publisher |
| `GET` | `/v1/publishers/{slug}` | None | Get publisher profile |

### Agents — Discovery (primary, token-efficient)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/v1/match` | None | Structured capability match |
| `GET` | `/v1/agents/{short_id}?fields=...` | None | Field-selective agent fetch |
| `POST` | `/v1/agents/batch` | None | Multi-agent batch fetch |
| `GET` | `/v1/taxonomy` | None | Capability taxonomy |

### Agents — Management

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/v1/agents` | Required | Register a new agent |
| `GET` | `/v1/agents` | None | List/filter agents |
| `GET` | `/v1/agents/{pub}/{slug}` | None | Get full agent card |
| `PATCH` | `/v1/agents/{pub}/{slug}` | Required (owner) | Update agent |
| `DELETE` | `/v1/agents/{pub}/{slug}` | Required (owner) | Archive agent |
| `GET` | `/v1/agents/{pub}/{slug}/versions` | None | Version history |

### Content negotiation

Pass the `Accept` header to control response verbosity:

| Accept header | Response format | Use case |
|---|---|---|
| `application/vnd.oar.compact+json` | Short keys (`n`, `c`, `ep`) | Agent-to-agent (default) |
| `application/json` | Full keys with descriptions | Human debugging, tooling |

### `GET /v1/agents` query parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `q` | string | — | Full-text search in name + description |
| `publisher` | string | — | Filter by publisher slug |
| `protocol` | string | — | Filter by protocol |
| `tag` | string | — | Filter by tag |
| `status` | string | `active` | `active`, `deprecated`, `archived` |
| `page` | int | `1` | Page number |
| `per_page` | int | `20` | Results per page (max 100) |

---

## Agent-to-Agent Integration Examples

### Python — full discovery flow

```python
import httpx
import json

REGISTRY = "http://localhost:8000"


def discover_agent(need: list[str], proto: str) -> dict | None:
    """Discover an agent and return its connection info."""
    # Stage 1: Match
    with httpx.Client(base_url=REGISTRY) as client:
        match = client.post("/v1/match", json={
            "need": need,
            "proto": proto,
            "limit": 3,
        }).json()

    if not match["r"]:
        return None

    best = match["r"][0]  # highest score
    agent_id = best["id"]

    # Stage 2: Get connection info
    with httpx.Client(base_url=REGISTRY) as client:
        info = client.get(
            f"/v1/agents/{agent_id}",
            params={"fields": "ep,auth"},
        ).json()

    return info


# Usage
connection = discover_agent(["code.review"], "a2a")
if connection:
    print(f"Connect to: {connection['endpoint']}")
    print(f"Auth: {connection['auth']}")
```

### Python — with local caching

```python
import time
import httpx

REGISTRY = "http://localhost:8000"

_cache: dict[str, tuple[dict, float]] = {}  # key -> (data, expires_at)


def match_cached(need: list[str], proto: str | None = None) -> list[dict]:
    """Match with local TTL cache — repeated calls cost 0 tokens."""
    cache_key = json.dumps({"need": need, "proto": proto}, sort_keys=True)

    if cache_key in _cache:
        data, expires_at = _cache[cache_key]
        if time.time() < expires_at:
            return data["r"]  # cache hit — 0 tokens

    with httpx.Client(base_url=REGISTRY) as client:
        resp = client.post("/v1/match", json={
            "need": need,
            "proto": proto,
            "limit": 5,
        })
    data = resp.json()

    ttl = data.get("ttl", 3600)
    _cache[cache_key] = (data, time.time() + ttl)

    return data["r"]
```

### Python — orchestrator discovering multiple agents

```python
import asyncio
import httpx

REGISTRY = "http://localhost:8000"


async def discover_team(requirements: list[dict]) -> list[dict]:
    """Discover multiple specialized agents in parallel."""
    async with httpx.AsyncClient(base_url=REGISTRY) as client:
        tasks = [
            client.post("/v1/match", json={**req, "limit": 1})
            for req in requirements
        ]
        responses = await asyncio.gather(*tasks)

    team = []
    for req, resp in zip(requirements, responses):
        results = resp.json().get("r", [])
        if results:
            team.append({"role": req["need"][0], "agent": results[0]})
    return team


async def main():
    team = await discover_team([
        {"need": ["code.review"], "proto": "a2a"},
        {"need": ["sec.scan"],    "proto": "a2a"},
        {"need": ["text.summarize"], "proto": "rest"},
    ])
    for member in team:
        print(f"{member['role']:20} → {member['agent']['n']} (score={member['agent']['s']})")


asyncio.run(main())
```

### Claude SDK — agent discovering a collaborator

```python
import anthropic
import httpx
import json

REGISTRY = "http://localhost:8000"

client = anthropic.Anthropic()


def find_agent_tool(need: list[str], proto: str = "a2a") -> str:
    """Tool function: find an agent and return its connection info."""
    with httpx.Client(base_url=REGISTRY) as http:
        # Stage 1
        match = http.post("/v1/match", json={"need": need, "proto": proto, "limit": 3}).json()
        if not match["r"]:
            return json.dumps({"error": "No agents found"})

        best_id = match["r"][0]["id"]

        # Stage 2
        info = http.get(f"/v1/agents/{best_id}", params={"fields": "ep,auth"}).json()

    return json.dumps(info)


tools = [{
    "name": "find_agent",
    "description": "Find a specialized AI agent in the registry by capability code",
    "input_schema": {
        "type": "object",
        "properties": {
            "need": {"type": "array", "items": {"type": "string"},
                     "description": "Required capability codes e.g. ['code.review']"},
            "proto": {"type": "string", "description": "Protocol: a2a, mcp, rest"}
        },
        "required": ["need"]
    }
}]

# The orchestrator agent can now discover collaborators
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    tools=tools,
    messages=[{
        "role": "user",
        "content": "I need to review some Python code. Find me a code review agent."
    }]
)

for block in response.content:
    if block.type == "tool_use" and block.name == "find_agent":
        result = find_agent_tool(**block.input)
        print("Found agent:", result)
```

### cURL — minimal shell script for CI/CD

```bash
#!/bin/bash
# discover-agent.sh — find a code reviewer and print its endpoint
set -e

REGISTRY="http://localhost:8000"

# Stage 1: match
MATCH=$(curl -sf -X POST "$REGISTRY/v1/match" \
  -H "Content-Type: application/json" \
  -d '{"need":["code.review"],"proto":"a2a","limit":1}')

AGENT_ID=$(echo "$MATCH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['r'][0]['id'] if d['r'] else '')")

if [ -z "$AGENT_ID" ]; then
  echo "No code review agent found" >&2
  exit 1
fi

# Stage 2: connection info
INFO=$(curl -sf "$REGISTRY/v1/agents/$AGENT_ID?fields=ep,auth")
ENDPOINT=$(echo "$INFO" | python3 -c "import sys,json; print(json.load(sys.stdin)['endpoint'])")

echo "Code reviewer endpoint: $ENDPOINT"
```

---

## Token Budget Guide

Understanding the token cost of different discovery patterns helps orchestrator agents manage their context window.

### Baseline: verbose API (not OAR)

A typical verbose registry returning full agent cards:

| Step | Action | Tokens consumed |
|---|---|---|
| List agents | `GET /agents?q=code+review` — 5 full cards | ~600 |
| Parse descriptions | LLM reads each card to decide | (already counted) |
| Fetch endpoint | `GET /agents/code-reviewer` — full card | ~300 |
| **Total** | | **~900 tokens** |

### OAR compact design

| Step | Action | Tokens consumed |
|---|---|---|
| Match | `POST /v1/match {"need":["code.review"]}` | ~60 |
| Inspect | `GET /v1/agents/3f9a2b1c?fields=ep,auth` | ~35 |
| **Total** | | **~100 tokens** |

**Savings: ~89%**

### With caching

| Step | Action | Tokens consumed |
|---|---|---|
| Match (cached) | Local TTL cache hit | 0 |
| Inspect (cached) | `If-None-Match` → 304 | 0 |
| **Total** | | **0 tokens** |

### Recommendations

1. **Cache taxonomy locally** — it changes maybe once a quarter. Load at startup, never fetch again during a session.

2. **Cache match results** — use the `ttl` field from the response. An orchestrator agent doing the same task repeatedly should never hit the registry twice for the same query within the TTL window.

3. **Use `?fields=ep,auth` always** — never fetch a full agent card if you only need to connect. The default `?fields=ep,auth` response is ~35 tokens; a full card is ~300.

4. **Use batch fetch for multi-agent coordination** — if your orchestrator selects 3 agents from a match result, one `POST /v1/agents/batch` call is cheaper than 3 individual fetches.

5. **Pick `limit` wisely** — requesting `limit=1` when you always pick the top result avoids processing unused candidates.

6. **Use `min_score`** — filtering to agents scoring 80+ means the LLM receives only genuinely capable candidates, not marginal matches it will discard anyway.

### Example: token budget for a 5-agent orchestration task

```
Initial taxonomy load:          0 tokens  (cached from startup)
Match agent 1 (code.review):   60 tokens
Match agent 2 (sec.scan):      60 tokens  (parallel, same cost)
Match agent 3 (text.summarize):60 tokens
Batch connect info (3 agents):  90 tokens
─────────────────────────────────────────
Total registry cost:           270 tokens
(vs ~4,500 tokens with verbose design)
```

The 4,230 tokens saved can be used for the actual task — analysis, reasoning, output — instead of parsing directory listings.
