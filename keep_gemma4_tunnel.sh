#!/bin/bash
# Keep Vast.ai Gemma 4 SSH tunnel alive — auto-reconnects on drop
# Usage: ./keep_gemma4_tunnel.sh &

LOCAL_PORT=11436
REMOTE_HOST="root@ssh6.vast.ai"
REMOTE_PORT=11353
LOG="/tmp/gemma4_tunnel.log"

echo "Starting Gemma 4 tunnel script..."

while true; do
    if ! curl -s --max-time 2 http://localhost:$LOCAL_PORT/api/tags >/dev/null 2>&1; then
        echo "$(date) Gemma 4 tunnel down — reconnecting..." >> "$LOG"
        pkill -f "ssh.*$LOCAL_PORT" 2>/dev/null
        sleep 1
        ssh -f -N -L $LOCAL_PORT:localhost:11434 \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 \
            -o ServerAliveInterval=30 \
            -o ServerAliveCountMax=3 \
            -o ExitOnForwardFailure=yes \
            -p $REMOTE_PORT $REMOTE_HOST 2>>"$LOG"
        if [ $? -eq 0 ]; then
            echo "$(date) Gemma 4 tunnel connected" >> "$LOG"
        else
            echo "$(date) Gemma 4 tunnel failed" >> "$LOG"
        fi
    fi
    sleep 30
done