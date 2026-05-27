#!/bin/bash
# Jarvis Keepalive — checks every minute, restarts if dead
JARVIS_DIR="/Users/nicholas/clawd/sovereign-temple"
VENV="$JARVIS_DIR/jarvis-env/bin/activate"
LOG="/tmp/jarvis_keepalive.log"

if ! pgrep -f "jarvis_compass.py" > /dev/null 2>&1; then
    echo "$(date): Jarvis not running, restarting..." >> "$LOG"
    cd "$JARVIS_DIR"
    source "$VENV" 2>/dev/null
    nohup python voice_pipeline/jarvis_compass.py >> /tmp/jarvis.log 2>&1 &
    echo "$(date): Jarvis restarted (PID: $!)" >> "$LOG"
else
    # Silently confirm running (only log every 10 min)
    MINUTE=$(date +%M)
    if [ $((MINUTE % 10)) -eq 0 ]; then
        echo "$(date): Jarvis alive (PID: $(pgrep -f jarvis_compass.py))" >> "$LOG"
    fi
fi
