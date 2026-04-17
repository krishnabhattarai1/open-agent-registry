<div align="center">

# Open Agent Registry (OAR)

**Token-optimized AI agent registry and discovery framework for agent-to-agent communication**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![CI](https://github.com/YOUR_USERNAME/open-agent-registry/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/open-agent-registry/actions/workflows/ci.yml)

</div>

---

OAR is an open-source registry where AI agents publish their capabilities and discover one another.  
Designed for **agent-to-agent (A2A) communication** — the primary consumers are LLMs, not humans.  
Every design decision prioritises minimising the tokens an agent must process to complete a discovery flow.

> **~89% token reduction** — a full discovery cycle costs ~100 tokens vs ~900 in a verbose design.

## How it works

OAR uses a **two-stage discovery protocol** — agents spend tokens on work, not on finding who to work with.

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    TWO-STAGE DISCOVERY PROTOCOL                         ║
╚══════════════════════════════════════════════════════════════════════════╝

  Agent A                    OAR Registry                    Agent B
    │                             │                               │
    │  ── STAGE 1: MATCH ─────────────────────────────────────── │
    │                             │                               │
    │  POST /v1/match             │                               │
    │  {                          │                               │
    │    "need": ["code.review"], │                               │
    │    "proto": "a2a",          │                               │
    │    "limit": 3               │                               │
    │  }                          │                               │
    │ ──────────────────────────► │                               │
    │                             │  lookup capability index      │
    │                             │  score & rank candidates      │
    │                             │  filter by protocol + auth    │
    │  ◄── ~60 tokens ─────────── │                               │
    │  {                          │                               │
    │    "r": [                   │                               │
    │      {"id":"3f9a","n":"CodeOwl",                            │
    │       "c":["code.review"],  │                               │
    │       "p":"a2a","s":95},    │ ← score 0-100                 │
    │      {"id":"7e2b","n":"LintBot",                            │
    │       "c":["code.review"],  │                               │
    │       "p":"a2a","s":81}     │                               │
    │    ],                       │                               │
    │    "t":2,"ttl":3600         │ ← cache for 1 hour            │
    │  }                          │                               │
    │                             │                               │
    │  picks best score (95) ─────│                               │
    │                             │                               │
    │  ── STAGE 2: CONNECT ───────────────────────────────────── │
    │                             │                               │
    │  GET /v1/agents/3f9a        │                               │
    │      ?fields=ep,auth        │ ← only fetch what's needed    │
    │ ──────────────────────────► │                               │
    │                             │                               │
    │  ◄── ~35 tokens ─────────── │                               │
    │  {                          │                               │
    │    "id": "3f9a",            │                               │
    │    "ep": "https://codeowl.ai/a2a",                          │
    │    "auth": {                │                               │
    │      "t": "bearer",         │                               │
    │      "url": "https://auth.codeowl.ai/token"                 │
    │    }                        │                               │
    │  }                          │                               │
    │                             │                               │
    │  ── STAGE 3: DIRECT (registry not involved) ─────────────  │
    │                             │                               │
    │  POST https://codeowl.ai/a2a (Bearer token)                 │
    │ ──────────────────────────────────────────────────────────► │
    │                             │                               │
    │  ◄── agent response ──────────────────────────────────────  │
    │                             │                               │

╔══════════════════════════════════════════════════════════════════════════╗
║  Total registry cost: ~95 tokens   (vs ~900 in a verbose design)        ║
║  Cached repeat lookup: 0 tokens    (ETag → 304 Not Modified)            ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### Discovery query options

```json
POST /v1/match
{
  "need":     ["code.review"],        ← required capabilities (all must match)
  "want":     ["code.fix"],           ← preferred (boosts score, not required)
  "proto":    "a2a",                  ← required protocol
  "auth":     ["bearer", "api_key"],  ← acceptable auth methods
  "io_in":    "text/x-diff",          ← input MIME type you will send
  "limit":    5,                      ← max results
  "min_score": 80                     ← quality threshold 0–100
}
```

## Features

- 🏷️ **Capability taxonomy** — 72 built-in codes (`code.review`, `data.transform`, `text.summarize`…) — agents match on codes, not verbose descriptions
- 🔍 **Structured matching** — `POST /v1/match` with `need`, `want`, `proto`, `auth`, `io_in` filters — server-side, no LLM parsing
- 📦 **Compact wire format** — short keys (`n`, `c`, `ep`, `s`) + field selection (`?fields=ep,auth`) — pay only for what you use
- ⚡ **ETags + TTL caching** — repeated lookups cost 0 tokens
- 🔑 **Multi-key auth** — multiple API keys per publisher, each independently enabled/disabled/deleted
- 📊 **Usage logging** — per-key metrics: request count, bytes in/out, estimated tokens, latency, top endpoints
- 🔌 **Multi-protocol** — A2A, MCP, ACP, REST, gRPC endpoint registration

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/open-agent-registry
cd open-agent-registry
./start.sh
```

Then open **http://localhost:7430/docs** for the interactive API docs.

## Usage example

```python
import httpx

REGISTRY = "http://localhost:7430"

# Stage 1: find a code reviewer (~60 tokens)
match = httpx.post(f"{REGISTRY}/v1/match", json={
    "need": ["code.review"],
    "proto": "a2a",
    "limit": 3,
}).json()

best = match["r"][0]          # highest score first

# Stage 2: get connection info only (~35 tokens)
info = httpx.get(
    f"{REGISTRY}/v1/agents/{best['id']}",
    params={"fields": "ep,auth"},
).json()

print(info["ep"])             # connect directly — registry is done
```

## API reference

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/match` | Structured capability match (primary discovery) |
| `GET` | `/v1/agents/{id}?fields=...` | Field-selective agent fetch |
| `POST` | `/v1/agents/batch` | Batch fetch multiple agents |
| `GET` | `/v1/taxonomy` | Browse 72 capability codes |
| `POST` | `/v1/publishers` | Register a publisher |
| `POST` | `/v1/agents` | Register an agent |
| `POST` | `/v1/keys` | Create an API key |
| `GET` | `/v1/keys/{id}/usage` | Usage stats for a key |

Full documentation → [docs/guide.md](docs/guide.md)

## Capability taxonomy

Agents register using structured codes — no natural language descriptions needed:

```
code:    review  gen  fix  lint  test  refactor  doc  debug
data:    transform  validate  enrich  clean  aggregate  parse
text:    summarize  translate  classify  extract  generate  embed
web:     scrape  browse  monitor  screenshot  api.call
search:  semantic  keyword  rag  vector
reason:  plan  math  decide  decompose  verify
media:   img.gen  img.edit  audio.transcribe  video.summarize
...and more
```

```bash
oar taxonomy          # browse all codes
oar match --need code.review --proto a2a
```

## Tech stack

- **Python 3.12** + **FastAPI** + **SQLAlchemy (async)**
- **PostgreSQL** with **pgvector** (ready for semantic search)
- **Alembic** migrations
- **Typer** CLI (`oar` command)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) — PRs welcome, especially new taxonomy codes and protocol adapters.

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities responsibly.

## Acknowledgements & Inspiration

See [NOTICE](NOTICE) for full attribution.

This project is inspired by research from:

- **MIT AI Agent Index** (2025) — [aiagentindex.mit.edu](https://aiagentindex.mit.edu)
- **MIT NANDA Initiative** — Networked Agents and Decentralized AI
- **AGNTCY Agent Directory** — DHT-based decentralised agent routing
- Agent interoperability standards: **A2A Protocol**, **MCP**, **ACP**, **CapIndex**

## License

[MIT](LICENSE) © OAR Contributors
