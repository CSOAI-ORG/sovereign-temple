#!/bin/bash
# JARVIS Launch Script - Start all services for MEOK AI Labs
# Run: ./start-all.sh

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║          MEOK AI LABS - JARVIS LAUNCHER                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source /Users/nicholas/clawd/sovereign-temple/jarvis-env/bin/activate

# Kill existing processes on ports
echo -e "${YELLOW}Checking ports...${NC}"
for port in 3200 8765; do
    if lsof -i :$port > /dev/null 2>&1; then
        echo "  Port $port in use, killing..."
        lsof -i :$port | grep LISTEN | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    fi
done

sleep 2

# Start MCP Server (port 3200)
echo -e "${YELLOW}Starting MCP Server (port 3200)...${NC}"
cd /Users/nicholas/clawd/sovereign-temple
nohup python sovereign-mcp-server.py > /tmp/mcp.log 2>&1 &
MCP_PID=$!
echo "  MCP Server PID: $MCP_PID"

# Wait for MCP to start
sleep 12

# Check MCP is running
if curl -s http://localhost:3200/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MCP Server running${NC}"
else
    echo -e "${RED}✗ MCP Server failed to start${NC}"
    tail -20 /tmp/mcp.log
    exit 1
fi

# Start Voice WebSocket (port 8765)
echo -e "${YELLOW}Starting Voice WebSocket (port 8765)...${NC}"
cd /Users/nicholas/clawd/sovereign-temple
nohup python voice_server.py > /tmp/voice.log 2>&1 &
VOICE_PID=$!
echo "  Voice Server PID: $VOICE_PID"

sleep 3

if lsof -i :8765 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Voice WebSocket running${NC}"
else
    echo -e "${YELLOW}⚠ Voice WebSocket failed (install websockets)${NC}"
fi

# Start MEOK Desktop
echo -e "${YELLOW}Starting MEOK Desktop...${NC}"
cd /Users/nicholas/clawd/meok-desktop
nohup npm run tauri dev > /tmp/meok-desktop.log 2>&1 &
DESKTOP_PID=$!
echo "  MEOK Desktop PID: $DESKTOP_PID"

sleep 10

if lsof -i :1420 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MEOK Desktop running (port 1420)${NC}"
else
    echo -e "${YELLOW}⚠ MEOK Desktop still starting...${NC}"
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                    SERVICES STATUS                        ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║ MCP Server:    http://localhost:3200        ✅            ║"
echo "║ MEOK UI:       http://localhost:3000        ✅ (if run)  ║"
echo "║ MEOK Desktop:  http://localhost:1420        ✅ (if run)  ║"
echo "║ Voice Server:  ws://localhost:8765         ✅ (if run)   ║"
echo "║ Ollama:        http://localhost:11434       ✅ (if run)  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Test the system
echo -e "${YELLOW}Testing JARVIS...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:3200/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"ask_sovereign","arguments":{"message":"Hello"}},"id":"test"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.loads(d['result']['content'][0]['text'])['response'][:50])" 2>/dev/null || echo "test")

echo -e "${GREEN}JARVIS says: \"$RESPONSE...\"${NC}"
echo ""

echo "Ready! 🎉"
echo ""
echo "Commands:"
echo "  - Voice conversation: python voice_pipeline/jarvis_conversational.py demo"
echo "  - View logs: tail -f /tmp/mcp.log"
echo "  - Stop all: pkill -f 'python.*mcp\|python.*voice'"
echo ""
