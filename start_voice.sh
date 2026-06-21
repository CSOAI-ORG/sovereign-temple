#!/bin/bash
# Start Sovereign Voice Interface

echo "🌟 Sovereign Temple Voice Interface"
echo "===================================="

# Kill any existing voice servers
pkill -f "voice_server" 2>/dev/null
echo "🛑 Stopped existing voice servers"

# Check MCP server
if ! curl -s http://localhost:3100/health > /dev/null; then
    echo "⚠️  MCP server not running. Starting Docker..."
    docker-compose up -d
    sleep 3
fi

# Start voice server
nohup python3 voice_server_minimal.py > /tmp/voice_server.log 2>&1 &
sleep 2

# Verify it's running
if lsof -ti:8765 > /dev/null; then
    echo "✅ Voice server running on ws://localhost:8765"
    echo ""
    echo "📱 Opening interfaces..."
    open chat.html  # Text chat
    # open voice_client.html  # Voice client (requires API key)
    echo ""
    echo "   Chat interface:     chat.html"
    echo "   Voice WebSocket:    ws://localhost:8765"
    echo ""
    echo "Press Ctrl+C to stop voice server"
    tail -f /tmp/voice_server.log
else
    echo "❌ Voice server failed to start"
    echo "Check /tmp/voice_server.log"
fi
