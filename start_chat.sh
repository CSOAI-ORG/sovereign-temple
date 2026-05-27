#!/bin/bash
# Start Sovereign Conversational Chat

echo "🌟 Sovereign Conversational Interface"
echo "======================================"

# Kill any existing servers
pkill -f "conversational_server" 2>/dev/null
pkill -f "voice_server" 2>/dev/null
echo "🛑 Stopped existing servers"

# Check MCP
if ! curl -s http://localhost:3100/health > /dev/null; then
    echo "🐳 Starting Docker services..."
    docker-compose up -d
    sleep 5
fi

# Check for OpenAI API key
if grep -q "sk-" .env 2>/dev/null && ! grep -q "PLACEHOLDER" .env; then
    echo "✅ OpenAI API key found - natural conversation enabled"
else
    echo "⚠️  No OpenAI API key - using fallback responses"
    echo "   Add OPENAI_API_KEY to .env for GPT-4 conversation"
fi

# Start conversational server
echo "🚀 Starting conversational server..."
nohup python3 conversational_server.py > /tmp/conv_server.log 2>&1 &
sleep 2

# Verify
if lsof -ti:8766 > /dev/null; then
    echo "✅ Conversational server running on ws://localhost:8766"
    echo ""
    echo "📱 Opening chat interface..."
    open chat.html
    echo ""
    echo "Usage:"
    echo "  🎤 Push-to-talk: Click mic, speak, release"
    echo "  🔄 Auto mode: Enable for continuous listening"  
    echo "  🔊 Voice: Toggle Sovereign's voice responses"
    echo "  ⌨️  Type: Press Enter to send"
    echo ""
    echo "Press Ctrl+C to stop"
    tail -f /tmp/conv_server.log
else
    echo "❌ Server failed to start"
    echo "Check /tmp/conv_server.log"
fi
