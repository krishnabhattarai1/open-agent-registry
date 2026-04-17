# Contributing to Open Agent Registry

Thank you for your interest in contributing! This document explains how to get set up, what we're looking for, and how to submit changes.

## Ways to contribute

- **Bug reports** — open an issue using the bug report template
- **New capability taxonomy codes** — propose additions via an issue before implementing
- **Protocol adapters** — new endpoint protocol support (A2A, MCP, ACP variants)
- **Documentation** — improvements to `docs/guide.md` or code comments
- **Tests** — more coverage is always welcome
- **Performance** — query optimisation, caching improvements

## Development setup

```bash
git clone https://github.com/YOUR_USERNAME/open-agent-registry
cd open-agent-registry

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Start PostgreSQL
docker compose up -d

# Run migrations
alembic upgrade head

# Start the API
uvicorn oar.main:app --reload --port 7430

# Run tests
pytest

# Lint and format
ruff check src/ tests/
ruff format src/ tests/
```

## Proposing new taxonomy codes

The capability taxonomy (`src/oar/taxonomy.py`) is the shared vocabulary that makes token-efficient discovery work. We want it to be broad but not bloated.

Before opening a PR for a new code:

1. Open an issue titled `[taxonomy] Add: domain.action`
2. Describe the use case and give 2–3 real agent examples that would use it
3. Confirm it doesn't overlap with an existing code (check `oar taxonomy`)
4. Wait for a maintainer to approve the addition

Approved codes are added to `taxonomy.py` and the taxonomy version is bumped.

## Pull request process

1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Make your changes with tests
3. Run the full test suite: `pytest`
4. Run lint: `ruff check src/ tests/`
5. Commit with a clear message (imperative mood: "Add webhook support", not "Added...")
6. Push and open a PR against `main`
7. Fill out the PR template — link the related issue

## Commit message style

```
type(scope): short description

Longer explanation if needed (wrap at 72 chars).

Fixes #123
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Code style

- Python 3.12+, type hints everywhere
- `ruff` for linting and formatting (config in `pyproject.toml`)
- Async-first: all DB calls use `async`/`await`
- Pydantic v2 for all schemas
- No bare `except:` — always catch specific exceptions

## Questions?

Open a discussion or issue. We're happy to help.
