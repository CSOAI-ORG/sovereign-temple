#!/bin/bash
# SOV3 Living Topology — Daemon Manager
#
# Manages all background services for the living topology:
#   1. NATS JetStream (event bus)
#   2. SOV3 Event Bridge (NATS → SOV3 memory)
#   3. File Watcher (filesystem → NATS + SOV3)
#   4. Topology Refresher (polls all sources, rebuilds graph)
#   5. Dashboard Server (serves 3D topology on :8888)
#
# Usage:
#   ./topology_daemons.sh start     # Start all daemons
#   ./topology_daemons.sh stop      # Stop all daemons
#   ./topology_daemons.sh status    # Show status
#   ./topology_daemons.sh restart   # Restart all
#   ./topology_daemons.sh logs      # Tail all logs

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWD_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="/tmp"
DASHBOARD_DIR="$CLAWD_DIR/topology-dashboard"

# PID files
NATS_PID="$LOG_DIR/nats-server.pid"
BRIDGE_PID="$LOG_DIR/sov3_event_bridge.pid"
WATCHER_PID="$LOG_DIR/sov3_file_watcher.pid"
REFRESHER_PID="$LOG_DIR/sov3_topology_refresh.pid"
DASHBOARD_PID="$LOG_DIR/topology_dashboard.pid"
ENSEMBLE_PID="$LOG_DIR/ensemble_engine.pid"

start_nats() {
    if pgrep -f "nats-server" > /dev/null 2>&1; then
        echo "  NATS: already running (PID $(pgrep -f nats-server))"
        return
    fi
    nats-server -js -p 4222 -m 8222 --store_dir /tmp/nats-data > "$LOG_DIR/nats.log" 2>&1 &
    echo $! > "$NATS_PID"
    echo "  NATS: started (PID $!)"
}

start_bridge() {
    if pgrep -f "sov3_event_bridge" > /dev/null 2>&1; then
        echo "  Bridge: already running (PID $(pgrep -f sov3_event_bridge))"
        return
    fi
    cd "$SCRIPT_DIR"
    python3 -u sov3_event_bridge.py > "$LOG_DIR/sov3_event_bridge.log" 2>&1 &
    echo $! > "$BRIDGE_PID"
    echo "  Bridge: started (PID $!)"
}

start_watcher() {
    if pgrep -f "sov3_file_watcher" > /dev/null 2>&1; then
        echo "  Watcher: already running (PID $(pgrep -f sov3_file_watcher))"
        return
    fi
    cd "$SCRIPT_DIR"
    python3 -u sov3_file_watcher.py > "$LOG_DIR/sov3_file_watcher.log" 2>&1 &
    echo $! > "$WATCHER_PID"
    echo "  Watcher: started (PID $!)"
}

start_refresher() {
    if pgrep -f "topology_refresh.*--daemon" > /dev/null 2>&1; then
        echo "  Refresher: already running (PID $(pgrep -f 'topology_refresh.*--daemon'))"
        return
    fi
    cd "$SCRIPT_DIR"
    python3 -u topology_refresh.py --daemon > "$LOG_DIR/topology_refresh.log" 2>&1 &
    echo $! > "$REFRESHER_PID"
    echo "  Refresher: started (PID $!)"
}

start_dashboard() {
    if lsof -i :8888 > /dev/null 2>&1; then
        echo "  Dashboard: already running on :8888"
        return
    fi
    # Build first
    cd "$DASHBOARD_DIR"
    python3 build.py --live > /dev/null 2>&1 || python3 build.py > /dev/null 2>&1
    cd "$DASHBOARD_DIR/dist"
    python3 -m http.server 8888 > "$LOG_DIR/topology_dashboard.log" 2>&1 &
    echo $! > "$DASHBOARD_PID"
    echo "  Dashboard: started at http://localhost:8888 (PID $!)"
}

start_ensemble() {
    if pgrep -f "ensemble_engine.*loop" > /dev/null 2>&1; then
        echo "  Ensemble: already running (PID $(pgrep -f 'ensemble_engine.*loop'))"
        return
    fi
    cd "$SCRIPT_DIR"
    python3 -u ensemble_engine.py loop > "$LOG_DIR/ensemble_engine.log" 2>&1 &
    echo $! > "$ENSEMBLE_PID"
    echo "  Ensemble: started (PID $!)"
}

stop_all() {
    echo "Stopping topology daemons..."
    # Don't stop NATS — other things may use it
    for proc in "sov3_event_bridge" "sov3_file_watcher" "topology_refresh.*--daemon" "ensemble_engine.*loop"; do
        pid=$(pgrep -f "$proc" 2>/dev/null)
        if [ -n "$pid" ]; then
            kill $pid 2>/dev/null
            echo "  Stopped $proc (PID $pid)"
        fi
    done
    # Stop dashboard server
    pid=$(lsof -ti :8888 2>/dev/null)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null
        echo "  Stopped dashboard (PID $pid)"
    fi
}

show_status() {
    echo "SOV3 Living Topology Status"
    echo "==========================="

    # NATS
    if pgrep -f "nats-server" > /dev/null 2>&1; then
        conns=$(curl -s http://localhost:8222/varz 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('connections',0))" 2>/dev/null || echo "?")
        echo "  NATS JetStream:   ✅ running (conns=$conns)"
    else
        echo "  NATS JetStream:   ❌ stopped"
    fi

    # SOV3
    sov3_status=$(curl -s http://localhost:3101/health 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d.get('status','?')} ({d['components']['consciousness']['consciousness_level']*100:.0f}%)\")" 2>/dev/null || echo "down")
    if [ "$sov3_status" != "down" ]; then
        echo "  SOV3:             ✅ $sov3_status"
    else
        echo "  SOV3:             ❌ not responding"
    fi

    # Bridge
    if pgrep -f "sov3_event_bridge" > /dev/null 2>&1; then
        echo "  Event Bridge:     ✅ running (PID $(pgrep -f sov3_event_bridge))"
    else
        echo "  Event Bridge:     ❌ stopped"
    fi

    # Watcher
    if pgrep -f "sov3_file_watcher" > /dev/null 2>&1; then
        echo "  File Watcher:     ✅ running (PID $(pgrep -f sov3_file_watcher))"
    else
        echo "  File Watcher:     ❌ stopped"
    fi

    # Refresher
    if pgrep -f "topology_refresh.*--daemon" > /dev/null 2>&1; then
        echo "  Topo Refresher:   ✅ running (PID $(pgrep -f 'topology_refresh.*--daemon'))"
    else
        echo "  Topo Refresher:   ❌ stopped"
    fi

    # Dashboard
    if lsof -i :8888 > /dev/null 2>&1; then
        echo "  Dashboard:        ✅ http://localhost:8888"
    else
        echo "  Dashboard:        ❌ stopped"
    fi

    # Ensemble
    if pgrep -f "ensemble_engine.*loop" > /dev/null 2>&1; then
        echo "  Ensemble Loop:    ✅ running (PID $(pgrep -f 'ensemble_engine.*loop'))"
    else
        echo "  Ensemble Loop:    ❌ stopped"
    fi

    # Hindsight
    hindsight=$(curl -s http://localhost:8765/v1/default/banks/meok-empire/stats 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"{d['total_nodes']}n/{d['total_links']}l\")" 2>/dev/null || echo "down")
    if [ "$hindsight" != "down" ]; then
        echo "  Hindsight:        ✅ $hindsight"
    else
        echo "  Hindsight:        ❌ not responding"
    fi

    # Hermes
    hermes=$(curl -s http://localhost:3000/health 2>/dev/null | python3 -c "import json,sys; print('connected')" 2>/dev/null || echo "disconnected")
    if [ "$hermes" = "connected" ]; then
        echo "  Hermes:           ✅ connected"
    else
        echo "  Hermes:           ⚠️  disconnected"
    fi

    # Ollama
    models=$(curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "0")
    if [ "$models" != "0" ]; then
        echo "  Ollama:           ✅ $models models"
    else
        echo "  Ollama:           ❌ not responding"
    fi
}

tail_logs() {
    echo "Tailing all topology logs (Ctrl+C to stop)..."
    tail -f "$LOG_DIR/sov3_event_bridge.log" "$LOG_DIR/sov3_file_watcher.log" "$LOG_DIR/topology_refresh.log" "$LOG_DIR/topology_dashboard.log" "$LOG_DIR/ensemble_engine.log" 2>/dev/null
}

case "${1:-status}" in
    start)
        echo "Starting topology daemons..."
        start_nats
        sleep 1
        start_bridge
        start_watcher
        start_refresher
        start_dashboard
        start_ensemble
        echo ""
        echo "All daemons started. Dashboard: http://localhost:8888"
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        echo ""
        echo "Starting topology daemons..."
        start_nats
        sleep 1
        start_bridge
        start_watcher
        start_refresher
        start_dashboard
        start_ensemble
        echo ""
        echo "All daemons restarted."
        ;;
    status)
        show_status
        ;;
    logs)
        tail_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
