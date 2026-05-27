#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# MEOKCLAW NEURAL BRIDGE TO VAST.AI v2.0
# Production-ready deployment bridge for remote GPU instances
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/Users/nicholas/clawd/sovereign-temple"
REMOTE_WORKSPACE="/workspace/meokclaw-sov3"
MESH_ORCHESTRATOR="${MESH_ORCHESTRATOR:-http://localhost:3202}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${BLUE}[BRIDGE]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${CYAN}[INFO]${NC} $1"; }

print_banner() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║         MEOKCLAW — NEURAL BRIDGE TO VAST.AI v2.0             ║"
    echo "║         Remote GPU Validation & Deployment Pipeline            ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
}

usage() {
    cat <<EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    deploy <ip> <port>      Full deploy + validation to Vast.ai instance
    validate <ip> <port>    Run validation suite only (no deploy)
    tunnel <ip> <port>      Establish SSH tunnel for Ollama
    sync <ip> <port>        Sync files only (no validation)
    status                  Check local mesh + tunnel status
    help                    Show this message

Environment:
    MESH_ORCHESTRATOR       URL of Mac Mesh orchestrator (default: http://localhost:3202)
    SSH_KEY                 Path to SSH private key (default: ~/.ssh/id_rsa)
    OLLAMA_PORT             Local port for Ollama tunnel (default: 11436)

Examples:
    $0 deploy 50.217.254.165 41600
    $0 tunnel 50.217.254.165 41600
    $0 validate 50.217.254.165 41600
EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# Deploy: sync files + setup + validate
# ─────────────────────────────────────────────────────────────────────────────
cmd_deploy() {
    local IP="${1:-}"
    local PORT="${2:-}"
    if [[ -z "$IP" || -z "$PORT" ]]; then
        err "Missing arguments. Usage: $0 deploy <ip> <port>"
        exit 1
    fi

    print_banner
    log "Target: root@$IP:$PORT"
    log "Mesh Orchestrator: $MESH_ORCHESTRATOR"

    # 1. Pre-flight checks
    log "Pre-flight checks..."
    if ! command -v rsync &>/dev/null; then
        err "rsync not found. Install with: brew install rsync"
        exit 1
    fi
    ok "rsync available"

    # 2. Check mesh orchestrator health
    log "Checking Mac Mesh orchestrator..."
    if curl -sf "$MESH_ORCHESTRATOR/health" >/dev/null 2>&1; then
        ok "Mesh orchestrator is healthy"
    else
        warn "Mesh orchestrator not responding at $MESH_ORCHESTRATOR"
        warn "Validation will skip mesh connectivity test"
    fi

    # 3. Create remote workspace
    log "Creating remote workspace..."
    ssh -p "$PORT" "root@$IP" "mkdir -p $REMOTE_WORKSPACE && echo 'Workspace ready'" || {
        err "Cannot SSH to $IP:$PORT. Check your Vast.ai dashboard for correct IP/port."
        exit 1
    }
    ok "Remote workspace ready"

    # 4. Sync core files
    log "Syncing sovereign substrate to remote..."
    rsync -avz --progress -e "ssh -p $PORT" \
        "$PROJECT_DIR/sovereign_architecture_v3.py" \
        "$PROJECT_DIR/vast_validation_suite.py" \
        "$PROJECT_DIR/quantization_profiles.yaml" \
        "$PROJECT_DIR/mac_mesh_orchestrator.py" \
        "$PROJECT_DIR/ollama_client.py" \
        "$PROJECT_DIR/alchemical_finetune_sov3.py" \
        "$PROJECT_DIR/sov3_continual_learning.py" \
        "root@$IP:$REMOTE_WORKSPACE/"
    ok "Files synced"

    # 5. Remote setup + validation
    log "Provisioning remote neural environment..."
    ssh -p "$PORT" "root@$IP" bash -s << REMOTE_EOF
        set -e
        echo "[REMOTE] Installing dependencies..."
        apt-get update -qq && apt-get install -y -qq python3-pip python3-venv curl
        
        cd $REMOTE_WORKSPACE
        python3 -m venv venv
        source venv/bin/activate
        
        echo "[REMOTE] Installing Python packages..."
        pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        pip install -q httpx numpy
        
        # Install Ollama if not present
        if ! command -v ollama &>/dev/null; then
            echo "[REMOTE] Installing Ollama..."
            curl -fsSL https://ollama.com/install.sh | sh
        fi
        
        # We skip pulling huge models here to prevent Out of Space errors on default Vast instances.
        # Ensure the server is running in the background for validation
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        sleep 5
        
        echo "[REMOTE] Pulling lightweight model for validation..."
        ollama pull gemma3:4b || echo "[REMOTE] gemma3:4b pull failed"
        
        # Run validation suite
        echo ""
        echo "[REMOTE] 🧪 Initiating Neural Handshake..."
        python3 vast_validation_suite.py --mesh-url "$MESH_ORCHESTRATOR" --ollama-url http://localhost:11434
        
        echo ""
        echo "[REMOTE] ✅ Setup complete. Ollama running on localhost:11434"
REMOTE_EOF

    ok "Remote validation complete"

    # 6. Establish tunnel
    log "Establishing SSH tunnel for Ollama..."
    establish_tunnel "$IP" "$PORT"

    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║              ✅ CLOUD BRIDGE DEPLOYMENT COMPLETE               ║"
    echo "╠════════════════════════════════════════════════════════════════╣"
    echo "║  Remote GPU:    root@$IP:$PORT                                ║"
    echo "║  Local Tunnel:  http://localhost:${OLLAMA_PORT:-11436}        ║"
    echo "║  Mesh Orch:     $MESH_ORCHESTRATOR                            ║"
    echo "║  Workspace:     $REMOTE_WORKSPACE                             ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    info "Test your cloud inference:"
    info "  curl http://localhost:${OLLAMA_PORT:-11436}/api/tags"
}

# ─────────────────────────────────────────────────────────────────────────────
# Validation only
# ─────────────────────────────────────────────────────────────────────────────
cmd_validate() {
    local IP="${1:-}"
    local PORT="${2:-}"
    if [[ -z "$IP" || -z "$PORT" ]]; then
        err "Missing arguments. Usage: $0 validate <ip> <port>"
        exit 1
    fi

    print_banner
    log "Running validation suite on root@$IP:$PORT..."

    ssh -p "$PORT" "root@$IP" bash -s << REMOTE_EOF
        cd $REMOTE_WORKSPACE
        source venv/bin/activate 2>/dev/null || true
        python3 vast_validation_suite.py --mesh-url "$MESH_ORCHESTRATOR" --ollama-url http://localhost:11434
REMOTE_EOF
}

# ─────────────────────────────────────────────────────────────────────────────
# SSH Tunnel
# ─────────────────────────────────────────────────────────────────────────────
cmd_tunnel() {
    local IP="${1:-}"
    local PORT="${2:-}"
    if [[ -z "$IP" || -z "$PORT" ]]; then
        err "Missing arguments. Usage: $0 tunnel <ip> <port>"
        exit 1
    fi

    establish_tunnel "$IP" "$PORT"
}

establish_tunnel() {
    local IP="$1"
    local PORT="$2"
    local LOCAL_PORT="${OLLAMA_PORT:-11436}"

    # Kill existing tunnel on same port
    if lsof -ti:"$LOCAL_PORT" >/dev/null 2>&1; then
        warn "Port $LOCAL_PORT already in use. Killing existing tunnel..."
        kill "$(lsof -ti:"$LOCAL_PORT")" 2>/dev/null || true
        sleep 1
    fi

    log "Starting SSH tunnel: localhost:$LOCAL_PORT → $IP:11434"
    ssh -N -L "$LOCAL_PORT:localhost:11434" -p "$PORT" "root@$IP" &
    TUNNEL_PID=$!
    echo $TUNNEL_PID > "$PROJECT_DIR/.vast_tunnel.pid"

    # Wait for tunnel
    sleep 2
    if kill -0 $TUNNEL_PID 2>/dev/null; then
        ok "Tunnel active (PID: $TUNNEL_PID) — localhost:$LOCAL_PORT → remote:11434"
    else
        err "Tunnel failed to start. Check SSH connectivity."
        exit 1
    fi

    # Test
    if curl -sf "http://localhost:$LOCAL_PORT/api/tags" >/dev/null 2>&1; then
        ok "Ollama reachable through tunnel"
    else
        warn "Tunnel active but Ollama not responding yet. Remote may still be starting."
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Sync only
# ─────────────────────────────────────────────────────────────────────────────
cmd_sync() {
    local IP="${1:-}"
    local PORT="${2:-}"
    if [[ -z "$IP" || -z "$PORT" ]]; then
        err "Missing arguments. Usage: $0 sync <ip> <port>"
        exit 1
    fi

    log "Syncing files to root@$IP:$PORT..."
    ssh -p "$PORT" "root@$IP" "mkdir -p $REMOTE_WORKSPACE"
    rsync -avz --progress -e "ssh -p $PORT" \
        "$PROJECT_DIR/sovereign_architecture_v3.py" \
        "$PROJECT_DIR/vast_validation_suite.py" \
        "$PROJECT_DIR/quantization_profiles.yaml" \
        "$PROJECT_DIR/mac_mesh_orchestrator.py" \
        "$PROJECT_DIR/alchemical_finetune_sov3.py" \
        "$PROJECT_DIR/sov3_continual_learning.py" \
        "root@$IP:$REMOTE_WORKSPACE/"
    ok "Sync complete"
}

# ─────────────────────────────────────────────────────────────────────────────
# Local status
# ─────────────────────────────────────────────────────────────────────────────
cmd_status() {
    print_banner
    log "Local mesh status:"

    # Check M4 orchestrator
    if curl -sf "http://localhost:3202/health" >/dev/null 2>&1; then
        ok "Mac Mesh Orchestrator: RUNNING (port 3202)"
    else
        warn "Mac Mesh Orchestrator: NOT RESPONDING"
    fi

    # Check M2 sidekick
    if curl -sf "http://m2-air.local:8080/health" >/dev/null 2>&1; then
        ok "M2 Sidekick: ONLINE"
    else
        warn "M2 Sidekick: OFFLINE"
    fi

    # Check Ollama local
    if curl -sf "http://localhost:11434/api/tags" >/dev/null 2>&1; then
        ok "Ollama (M4 local): RUNNING"
    else
        warn "Ollama (M4 local): NOT RESPONDING"
    fi

    # Check Vast tunnel
    local LOCAL_PORT="${OLLAMA_PORT:-11436}"
    if curl -sf "http://localhost:$LOCAL_PORT/api/tags" >/dev/null 2>&1; then
        ok "Vast.ai Tunnel: ACTIVE (localhost:$LOCAL_PORT)"
    else
        warn "Vast.ai Tunnel: INACTIVE"
    fi

    # Check tunnel PID
    if [[ -f "$PROJECT_DIR/.vast_tunnel.pid" ]]; then
        local PID
        PID=$(cat "$PROJECT_DIR/.vast_tunnel.pid")
        if kill -0 "$PID" 2>/dev/null; then
            info "Tunnel PID: $PID"
        else
            warn "Tunnel PID file exists but process dead (stale PID: $PID)"
        fi
    fi

    # Check SOV3
    if curl -sf "http://localhost:3101/mcp/coord_get_dashboard" >/dev/null 2>&1; then
        ok "SOV3 Coordination: RUNNING (port 3101)"
    else
        warn "SOV3 Coordination: NOT RESPONDING"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
    deploy)
        cmd_deploy "$@"
        ;;
    validate)
        cmd_validate "$@"
        ;;
    tunnel)
        cmd_tunnel "$@"
        ;;
    sync)
        cmd_sync "$@"
        ;;
    status)
        cmd_status
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        err "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac
