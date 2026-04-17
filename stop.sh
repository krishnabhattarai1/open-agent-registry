#!/bin/bash
# stop.sh — shut down Open Agent Registry (API server + PostgreSQL)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${CYAN}  $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Open Agent Registry — Stopping     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Stop uvicorn (any process on port 7430) ────────────────────────────────────
PORT="${OAR_PORT:-7430}"
info "Stopping API server on port $PORT..."
PIDS=$(lsof -ti tcp:"$PORT" 2>/dev/null || true)
if [ -n "$PIDS" ]; then
  echo "$PIDS" | xargs kill -TERM 2>/dev/null || true
  sleep 1
  ok "API server stopped"
else
  warn "No API server running on port $PORT"
fi

# ── Stop PostgreSQL ────────────────────────────────────────────────────────────
info "Stopping PostgreSQL (docker compose down)..."
if docker info &>/dev/null 2>&1; then
  docker compose down 2>&1 | grep -E "(Stopped|Removed|removed)" || true
  ok "PostgreSQL stopped"
else
  warn "Docker not running — nothing to stop"
fi

echo ""
echo -e "${GREEN}  All services stopped.${NC}"
echo ""
