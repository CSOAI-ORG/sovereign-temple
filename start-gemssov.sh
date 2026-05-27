#!/bin/bash
#
# GemSov Launcher - Start Gemma 4 + SOV3 + Jarvis
# Opens the unified UI
#

echo "🐉 Starting GemSov - Gemma 4 + SOV3 Unified System"
echo "=================================================="

# Check if Gemma 4 server is running
echo ""
echo "1. Checking API server (port 8700)..."
if lsof -i :8700 > /dev/null 2>&1; then
    echo "   ✅ API server already running"
else
    echo "   ⚠️  Starting API server in background..."
    cd /Users/nicholas/clawd/sovereign-temple
    nohup /opt/homebrew/bin/python3.11 gemma4_sov3_server.py > /tmp/gemssov.log 2>&1 &
    sleep 3
fi

# Check SOV3
echo ""
echo "2. Checking SOV3 (port 3100/3200)..."
if lsof -i :3200 > /dev/null 2>&1; then
    echo "   ✅ SOV3 MCP running"
elif lsof -i :3100 > /dev/null 2>&1; then
    echo "   ✅ SOV3 MCP running on 3100"
else
    echo "   ⚠️  SOV3 not detected - will use mock mode"
fi

# Check Ollama
echo ""
echo "3. Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "   ✅ Ollama running"
else
    echo "   ⚠️  Ollama not detected"
fi

# Open UI
echo ""
echo "4. Opening GemSov Jarvis OS..."
open /Users/nicholas/clawd/sovereign-temple/gemssov-jarvis-os.html

echo ""
echo "=================================================="
echo "🐉 GemSov is ready!"
echo ""
echo "UI:       file://.../gemma4-jarvis-os.html"
echo "API:      http://localhost:8700"
echo "Docs:     http://localhost:8700/docs"
echo ""
echo "Press Ctrl+C to stop background services"
echo ""

# Keep running
wait
