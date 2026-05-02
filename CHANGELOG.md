# Changelog

All notable changes to Open Agent Registry (OAR) are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-05-02

### Added

**Core registry**
- Two-stage discovery protocol: `POST /v1/match` (Stage 1, ~60 tokens) → `GET /v1/agents/{id}?fields=...` (Stage 2, ~35 tokens) → direct agent-to-agent connection (Stage 3, registry not involved)
- Compact wire format with short keys (`n`, `c`, `ep`, `s`, `r`, `t`, `ttl`) — ~89% token reduction vs verbose designs
- Field selection via `?fields=ep,auth,caps` — agents pay only for the fields they need
- ETag + TTL caching — repeated lookups cost 0 tokens via `If-None-Match` → 304

**Capability taxonomy**
- 72 built-in capability codes across 12 domains (`code`, `data`, `text`, `web`, `search`, `reason`, `media`, `file`, `db`, `sec`, `infra`, `comms`)
- Structured matching: `need` (all-of), `want` (score boost), prefix matching (`code` matches all `code.*`), `any`, `not` combinators
- `GET /v1/taxonomy` endpoint (7-day cache)

**Publisher & agent management**
- Publisher registration (`POST /v1/publishers`) with API key returned once on creation
- Agent CRUD: register, list, get (verbose + compact), update, soft-delete/archive
- Agent card manifest (`agent-card.yaml`) with capability codes, I/O MIME types, multi-protocol endpoints
- Immutable version snapshots (`agent_versions` table)

**Multi-key authentication**
- Multiple API keys per publisher — each independently enabled, disabled, or deleted (soft)
- `POST /v1/keys`, `GET /v1/keys`, `PATCH /v1/keys/{id}/status`, `DELETE /v1/keys/{id}`

**Usage logging**
- Per-key metrics via `GET /v1/keys/{id}/usage`: request count, bytes in/out, estimated tokens, avg latency, HTTP status breakdown, top 5 endpoints
- Paginated raw logs via `GET /v1/keys/{id}/logs`
- Async middleware — logging never slows down or fails a request

**CLI (`oar`)**
- `oar config set registry-url / api-key`
- `oar register / publish` — create or update from `agent-card.yaml`
- `oar match --need <code> --proto <proto>`
- `oar search`, `oar list`, `oar info`, `oar validate`, `oar taxonomy`

**Developer tooling**
- `start.sh` — single-command bootstrap (uv/venv, Docker, migrations, uvicorn on port 7430)
- `stop.sh` — stop server and Docker services
- Alembic migrations (`001_initial`, `002_api_keys`)
- Full async test suite (pytest + coverage) with pgvector Docker service
- CI pipeline (GitHub Actions): lint (ruff) + test matrix (Python 3.12 & 3.13)
- MIT license, NOTICE attribution, CITATIONS.cff, CONTRIBUTING.md, SECURITY.md

### Tech stack

- Python 3.12, FastAPI 0.115, SQLAlchemy (async), asyncpg, Alembic
- PostgreSQL 16 with pgvector (ready for semantic search)
- Typer CLI, Rich, httpx, bcrypt, PyYAML, pydantic-settings

[0.1.0]: https://github.com/krishnabhattarai1/open-agent-registry/releases/tag/v0.1.0
