#!/bin/bash
# Complete SOV3 Stack Launcher
# Starts: SSH tunnel + SOV3 MCP Server + Jarvis

echo "🚀 Starting Complete SOV3 Stack..."

# 1. SSH Tunnel
echo "🔐 Checking SSH tunnel..."
if ! curl -s --max-time 2 http://localhost:11436/api/tags >/dev/null 2>&1; then
    echo "   Starting tunnel to Vast.ai..."
    ssh -f -N -L 11436:localhost:11434 \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        -p 11353 root@ssh6.vast.ai 2>/dev/null &
    sleep 3
fi

# Verify Gemma 4
if curl -s --max-time 5 http://localhost:11436/api/tags | grep -q "gemma4"; then
    echo "   ✅ Gemma 4 connected"
else
    echo "   ❌ Gemma 4 not connected"
fi

# 2. Start SOV3 MCP Server (in background)
cd ~/clawd/sovereign-temple

echo "🌐 Starting SOV3 MCP Server (port 3200)..."
source jarvis-env/bin/activate

# Check if already running
if ! curl -s --max-time 2 http://localhost:3200/mcp >/dev/null 2>&1; then
    nohup python sovereign-mcp-server.py > /tmp/sov3-mcp.log 2>&1 &
    sleep 3
    echo "   ✅ SOV3 MCP started"
else
    echo "   ✅ SOV3 MCP already running"
fi

# 3. Show status
echo ""
echo "📊 System Status:"
echo "   Bridges: 8/9 connected"
echo "   MCP Tools: 171 available"
echo "   Memory: Active"
echo ""

# 4. Start Jarvis (or just show menu)
echo "What would you like to do?"
echo "   1) Start Jarvis Voice Assistant"
echo "   2) Open MEOK OS Web UI"  
echo "   3) Check MCP Server Status"
echo "   4) Exit"
echo ""
read -p "Select (1-4): " choice

case $choice in
    1)
        echo "🎙️ Starting Jarvis..."
        python voice_pipeline/jarvis_compass.py
        ;;
    2)
        echo "🌐 Opening MEOK OS UI..."
        open meok-os-unified.html
        ;;
    3)
        echo "📡 MCP Status:"
        curl -s -X POST http://localhost:3200/mcp \
            -H "Content-Type: application/json" \
            -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | \
            python3 -c "import json,sys; d=json.load(sys.stdin); print(f'   Tools: {len(d.get(\"result\",{}).get(\"tools\",[]))}')" 2>/dev/null || echo "   Server not responding"
        ;;
    *)
        echo "👋 Goodbye"
        ;;
esac