#!/bin/bash
# start.sh — one-command startup for Open Agent Registry
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

VENV="$PROJECT_DIR/.venv"
PYTHON="$VENV/bin/python"
ALEMBIC="$VENV/bin/alembic"
UVICORN="$VENV/bin/uvicorn"
OAR="$VENV/bin/oar"

# ── Colours ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${CYAN}  $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Open Agent Registry — Startup      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Python check ───────────────────────────────────────────────────────
info "Checking Python..."
if ! command -v python3 &>/dev/null; then
  fail "python3 not found. Install Python 3.12+ and re-run."
fi
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYVER"

# ── Step 2: Virtual environment ─────────────────────────────────────────────
info "Setting up virtual environment..."
if [ ! -d "$VENV" ]; then
  if command -v uv &>/dev/null; then
    uv venv "$VENV" --python python3 2>&1 | grep -v "^$" || true
  else
    python3 -m venv "$VENV"
  fi
  ok "Created .venv"
else
  ok ".venv already exists"
fi

# ── Step 3: Install dependencies ───────────────────────────────────────────────
info "Installing dependencies..."
"$VENV/bin/pip" install -e ".[dev]" -q
ok "Dependencies installed"

# ── Step 4: Docker Desktop ─────────────────────────────────────────────────────
info "Checking Docker..."
if ! command -v docker &>/dev/null; then
  fail "Docker not found. Install Docker Desktop from https://docker.com and re-run."
fi

if ! docker info &>/dev/null 2>&1; then
  warn "Docker daemon not running — starting Docker Desktop..."
  open -a Docker 2>/dev/null || true
  echo -n "  Waiting for Docker"
  for i in $(seq 1 30); do
    sleep 2
    echo -n "."
    if docker info &>/dev/null 2>&1; then
      echo ""
      ok "Docker is ready"
      break
    fi
    if [ "$i" -eq 30 ]; then
      echo ""
      fail "Docker did not start within 60 seconds. Open Docker Desktop manually and re-run."
    fi
  done
else
  ok "Docker is running"
fi

# ── Step 5: Start PostgreSQL ────────────────────────────────────────────────────
info "Starting PostgreSQL (docker compose)..."
docker compose up -d 2>&1 | grep -E "(Started|Running|healthy|up-to-date|Created)" || true

echo -n "  Waiting for PostgreSQL to accept connections"
for i in $(seq 1 20); do
  sleep 1
  echo -n "."
  if docker compose exec -T db pg_isready -U oar -q 2>/dev/null; then
    echo ""
    ok "PostgreSQL is ready"
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo ""
    fail "PostgreSQL did not become ready in time. Check: docker compose logs db"
  fi
done

# ── Step 6: Run migrations ─────────────────────────────────────────────────────
info "Running database migrations..."
OAR_DATABASE_URL="postgresql+asyncpg://oar:oar_dev@localhost:5432/oar" \
  "$ALEMBIC" upgrade head 2>&1 | tail -5
ok "Database schema is up to date"

# ── Step 7: Launch API server ──────────────────────────────────────────────────
PORT="${OAR_PORT:-7430}"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Registry is starting on port $PORT${NC}"
echo -e "${GREEN}  API docs → http://localhost:$PORT/docs${NC}"
echo -e "${GREEN}  Health   → http://localhost:$PORT/health${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop the server"
echo ""

OAR_DATABASE_URL="postgresql+asyncpg://oar:oar_dev@localhost:5432/oar" \
OAR_PORT="$PORT" \
  "$UVICORN" oar.main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --reload
