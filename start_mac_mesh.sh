#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# START_MAC_MESH.sh — Launch the entire Dual-Mac Inference Mesh
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   On M4 (command center):
#     ./start_mac_mesh.sh m4
#
#   On M2 (sidekick):
#     ./start_mac_mesh.sh m2
#
#   Dashboard only:
#     ./start_mac_mesh.sh dashboard
#
# ═══════════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-m4}"
LOG_DIR="$HOME/clawd/memory/mesh_logs"
mkdir -p "$LOG_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[MESH]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

check_ollama() {
    if ! curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
        warn "Ollama not running on localhost:11434"
        warn "Start with: ollama serve"
        return 1
    fi
    success "Ollama is running"
    return 0
}

check_m2_reachable() {
    if ! ping -c 1 -W 2 m2-air.local >/dev/null 2>&1; then
        warn "M2 (m2-air.local) not reachable via ping"
        warn "Check WiFi/Bluetooth or set M2_HOST env var"
        return 1
    fi
    success "M2 is reachable"
    return 0
}

start_m2() {
    log "Starting M2 Sidekick v2..."
    check_ollama || exit 1

    # Pull recommended models if not present
    log "Checking models..."
    for model in qwen3:0.6b nomic-embed-text qwen3:4b; do
        if ! ollama list | grep -q "$model"; then
            warn "Model $model not found. Pulling..."
            ollama pull "$model"
        fi
    done

    log "Launching M2 Sidekick v2 on port 8080"
    python3 legion-omega/trinity/m2_sidekick_v2.py &
    M2_PID=$!
    echo $M2_PID > "$LOG_DIR/m2_sidekick.pid"
    success "M2 Sidekick started (PID: $M2_PID)"

    log "Services:"
    echo "  • API:      http://$(hostname):8080"
    echo "  • Health:   http://$(hostname):8080/health"
    echo "  • Metrics:  http://$(hostname):8080/metrics"
}

start_m4() {
    log "Starting M4 Mesh Command Center..."
    check_ollama || exit 1
    check_m2_reachable || warn "M2 not reachable — mesh will be degraded"

    # Pull recommended models
    log "Checking models..."
    for model in qwen3:4b qwen3:8b qwen3-coder:8b gemma3:12b; do
        if ! ollama list | grep -q "$model"; then
            warn "Model $model not found. Pulling..."
            ollama pull "$model"
        fi
    done

    log "Launching Mac Mesh Orchestrator on port 3202"
    python3 mac_mesh_orchestrator.py &
    ORCH_PID=$!
    echo $ORCH_PID > "$LOG_DIR/mesh_orchestrator.pid"
    success "Orchestrator started (PID: $ORCH_PID)"

    sleep 2

    log "Launching Mesh Health Dashboard on port 9090"
    python3 mesh_health_dashboard.py --mode api --port 9090 &
    DASH_PID=$!
    echo $DASH_PID > "$LOG_DIR/mesh_dashboard.pid"
    success "Dashboard started (PID: $DASH_PID)"

    log "Services:"
    echo "  • Orchestrator:  http://$(hostname):3202"
    echo "  • Health:        http://$(hostname):3202/health"
    echo "  • Chat:          POST http://$(hostname):3202/v1/chat"
    echo "  • Dashboard:     http://$(hostname):9090"
    echo "  • Prometheus:    http://$(hostname):9090/metrics"
    echo ""
    echo "  • Siri:          http://$(hostname):3202/siri/chat?message=..."
    echo ""
    echo "Test commands:"
    echo "  curl http://$(hostname):3202/health"
    echo "  curl 'http://$(hostname):3202/v1/route?query=explain+quantum+computing'"
    echo "  curl -X POST http://$(hostname):3202/v1/chat -H 'Content-Type: application/json' -d '{\"message\":\"Hello\"}'"
}

start_dashboard() {
    log "Starting Mesh Health Dashboard (terminal mode)..."
    python3 mesh_health_dashboard.py --mode terminal --port 9090
}

stop_all() {
    log "Stopping all mesh services..."
    for pidfile in "$LOG_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            PID=$(cat "$pidfile")
            NAME=$(basename "$pidfile" .pid)
            if kill -0 "$PID" 2>/dev/null; then
                kill "$PID"
                success "Stopped $NAME (PID: $PID)"
            fi
            rm -f "$pidfile"
        fi
    done
}

status() {
    log "Mesh service status:"
    for pidfile in "$LOG_DIR"/*.pid; do
        if [ -f "$pidfile" ]; then
            PID=$(cat "$pidfile")
            NAME=$(basename "$pidfile" .pid)
            if kill -0 "$PID" 2>/dev/null; then
                success "$NAME: running (PID: $PID)"
            else
                error "$NAME: not running (stale PID: $PID)"
            fi
        fi
    done

    echo ""
    log "Node health:"
    curl -sf http://localhost:3202/health 2>/dev/null | python3 -m json.tool 2>/dev/null || warn "Orchestrator not responding"
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

case "$MODE" in
    m2)
        start_m2
        ;;
    m4)
        start_m4
        ;;
    dashboard)
        start_dashboard
        ;;
    stop)
        stop_all
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {m2|m4|dashboard|stop|status}"
        echo ""
        echo "  m2        — Start M2 Sidekick v2 (run on MacBook Air M2)"
        echo "  m4        — Start M4 Orchestrator + Dashboard (run on MacBook M4)"
        echo "  dashboard — Start terminal dashboard only"
        echo "  stop      — Stop all mesh services"
        echo "  status    — Show service status"
        exit 1
        ;;
esac
