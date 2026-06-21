#!/bin/bash
# Keep GPU SSH tunnel alive — auto-reconnects on drop
# Usage: ./keep_tunnel_alive.sh &

LOCAL_PORT=11435
REMOTE_HOST="root@50.217.254.165"
REMOTE_PORT=41724
LOG="/tmp/gpu_tunnel.log"

while true; do
    if ! curl -s --max-time 2 http://localhost:$LOCAL_PORT/api/tags >/dev/null 2>&1; then
        echo "$(date) Tunnel down — reconnecting..." >> "$LOG"
        pkill -f "ssh.*$LOCAL_PORT" 2>/dev/null
        sleep 1
        ssh -f -N -L $LOCAL_PORT:localhost:11434 \
            -o StrictHostKeyChecking=no \
            -o ConnectTimeout=5 \
            -o ServerAliveInterval=15 \
            -o ServerAliveCountMax=4 \
            -o ExitOnForwardFailure=yes \
            -p $REMOTE_PORT $REMOTE_HOST 2>>"$LOG"
        echo "$(date) Tunnel reconnected" >> "$LOG"
    fi
    sleep 30
done
