#!/bin/bash
# MEOKCLAW Research Swarm Scheduler
# Runs the research swarm every 12 hours continuously

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS_DIR="$SCRIPT_DIR/reports"
LOGS_DIR="$SCRIPT_DIR/logs"
PIDFILE="$SCRIPT_DIR/swarm.pid"

mkdir -p "$REPORTS_DIR" "$LOGS_DIR"

start() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Research swarm already running (PID: $(cat $PIDFILE))"
        exit 1
    fi

    echo "🚀 Starting MEOKCLAW Research Swarm..."
    echo "   Interval: 12 hours"
    echo "   Reports: $REPORTS_DIR"
    echo "   Logs: $LOGS_DIR"
    echo

    nohup python3 "$SCRIPT_DIR/orchestrator.py" \
        --continuous \
        --interval 12 \
        --output "$REPORTS_DIR" \
        > "$LOGS_DIR/swarm.log" 2>&1 &

    echo $! > "$PIDFILE"
    echo "   PID: $(cat $PIDFILE)"
    echo "   Log: tail -f $LOGS_DIR/swarm.log"
}

stop() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Stopping research swarm (PID: $PID)..."
            kill "$PID"
            rm -f "$PIDFILE"
            echo "   Stopped."
        else
            echo "   Process not running. Cleaning up."
            rm -f "$PIDFILE"
        fi
    else
        echo "   No PID file found."
    fi
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "✅ Research swarm running (PID: $(cat $PIDFILE))"
        echo "   Last report: $(ls -t $REPORTS_DIR/*.md 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo 'None yet')"
    else
        echo "❌ Research swarm not running"
    fi
}

run_once() {
    echo "🔬 Running single research scan..."
    python3 "$SCRIPT_DIR/orchestrator.py" --output "$REPORTS_DIR"
}

case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 2
        start
        ;;
    status)
        status
        ;;
    once)
        run_once
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|once}"
        exit 1
        ;;
esac
