#!/bin/bash
# SOV3 — Local dev start script (no Docker needed)
# Uses Homebrew PostgreSQL 15 on localhost:5432
# Runs on port 3101 to avoid OrbStack conflict on 3100
#
# Usage:
#   ./run-local.sh          — start SOV3
#   ./run-local.sh stop     — kill running SOV3
#   ./run-local.sh status   — check health

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
LOG_FILE="/tmp/sov3.log"
PID_FILE="/tmp/sov3.pid"

if [[ "$1" == "stop" ]]; then
  if [[ -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null && echo "✅ SOV3 stopped" || echo "⚠️  Already stopped"
    rm -f "$PID_FILE"
  else
    pkill -f "sovereign-mcp-server" 2>/dev/null && echo "✅ SOV3 stopped" || echo "⚠️  Not running"
  fi
  exit 0
fi

if [[ "$1" == "status" ]]; then
  PORT=$(grep "^PORT=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "3101")
  echo "🔍 Checking SOV3 health on port $PORT..."
  curl -s "http://localhost:$PORT/health" | python3 -m json.tool 2>/dev/null | grep -E "status|memory_store|consciousness_mode" || echo "❌ SOV3 not responding"
  exit 0
fi

# Check PostgreSQL is running
if ! pg_isready -q 2>/dev/null; then
  echo "⚠️  PostgreSQL not running. Starting..."
  brew services start postgresql@15 2>/dev/null || brew services start postgresql 2>/dev/null
  sleep 2
fi

# Determine Python interpreter (prefer venv)
PYTHON="$SCRIPT_DIR/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

# Source .env
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
  echo "✅ Loaded env from $ENV_FILE"
else
  echo "⚠️  No .env found, using defaults (PORT=3101)"
  export PORT=3101
  export POSTGRES_DSN="postgresql://sovereign:sovereign@localhost:5432/sovereign_memory"
  export APP_ENV=development
fi

echo "🚀 Starting SOV3 on port $PORT..."
cd "$SCRIPT_DIR"
unset MallocStackLogging 2>/dev/null
"$PYTHON" sovereign-mcp-server.py > "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "   PID: $(cat "$PID_FILE") | Log: $LOG_FILE"

# Wait for health
for i in {1..15}; do
  sleep 1
  if curl -s "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo "✅ SOV3 healthy on http://localhost:$PORT"
    echo ""
    echo "   MCP endpoint: http://localhost:$PORT/mcp"
    echo "   Health:       http://localhost:$PORT/health"
    echo "   Stop:         ./run-local.sh stop"

    # Warm up Gemma 4 in background (prevents 60s cold-load on first voice call)
    if command -v ollama &> /dev/null; then
      echo ""
      echo "🔥 Warming up Gemma 4..."
      (ollama run gemma4:e4b "ready" --keepalive 30m > /dev/null 2>&1 && echo "   ✅ Gemma 4 warm (30min keepalive)") &
    fi
    exit 0
  fi
  echo "   Waiting... ($i/15)"
done

echo "❌ SOV3 failed to start. Check logs:"
echo "   tail -50 $LOG_FILE"
exit 1
