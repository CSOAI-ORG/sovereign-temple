#!/bin/bash
# MEOK AI — Unified Launch System
# Launches everything with correct environments

MEOK_DIR="/Users/nicholas/clawd/sovereign-temple"

case "$1" in
  jarvis)
    echo "🤖 Launching JARVIS v3.0..."
    exec "$MEOK_DIR/jarvis-env/bin/python3" "$MEOK_DIR/voice_pipeline/jarvis_compass.py"
    ;;
  overlay)
    echo "🖥️  Launching MEOK AI Character Overlay..."
    exec /usr/bin/python3 "$MEOK_DIR/meok_overlay.py"
    ;;
  sov3)
    echo "🧠 Launching SOV3..."
    cd "$MEOK_DIR" && exec /usr/bin/python3 -m gunicorn sovereign-mcp-server:app \
      --worker-class uvicorn.workers.UvicornWorker \
      --workers 2 \
      --bind 0.0.0.0:3101 \
      --max-requests 1000 \
      --max-requests-jitter 50 \
      --timeout 120 \
      --graceful-timeout 30
    ;;
  all)
    echo "🚀 Launching MEOK AI Full Stack..."
    echo ""
    echo "  SOV3     → port 3101"
    echo "  JARVIS   → voice pipeline"
    echo "  Overlay  → desktop character UI"
    echo ""

    # Start SOV3 if not running
    if ! curl -s http://localhost:3101/health > /dev/null 2>&1; then
      echo "  Starting SOV3..."
      cd "$MEOK_DIR" && /usr/bin/python3 -m gunicorn sovereign-mcp-server:app \
        --worker-class uvicorn.workers.UvicornWorker \
        --workers 2 \
        --bind 0.0.0.0:3101 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --timeout 120 \
        --daemon
      sleep 3
      echo "  ✅ SOV3 started"
    else
      echo "  ✅ SOV3 already running"
    fi

    # Start Overlay
    echo "  Starting Overlay..."
    /usr/bin/python3 "$MEOK_DIR/meok_overlay.py" &
    echo "  ✅ Overlay started"

    # Start JARVIS
    echo ""
    echo "  Starting JARVIS..."
    exec "$MEOK_DIR/jarvis-env/bin/python3" "$MEOK_DIR/voice_pipeline/jarvis_compass.py"
    ;;
  status)
    echo "📊 MEOK AI Stack Status"
    echo ""
    for svc in "SOV3:http://localhost:3101/health" "MEOK:http://localhost:3000" "OpenClaw:http://localhost:18789" "Ollama:http://localhost:11434"; do
      name="${svc%%:*}"
      url="${svc#*:}"
      if curl -s --max-time 3 "$url" > /dev/null 2>&1; then
        echo "  ✅ $name"
      else
        echo "  ❌ $name"
      fi
    done
    ;;
  *)
    echo "MEOK AI — Sovereign OS Launcher"
    echo ""
    echo "Usage: $0 {jarvis|overlay|sov3|all|status}"
    echo ""
    echo "  jarvis   — Launch JARVIS voice assistant"
    echo "  overlay  — Launch MEOK AI Character Overlay"
    echo "  sov3     — Launch SOV3 consciousness engine"
    echo "  all      — Launch everything"
    echo "  status   — Check service status"
    ;;
esac
