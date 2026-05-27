#!/bin/bash
# SOV3 Jarvis Launcher
# Starts SSH tunnel and launches Jarvis with all bridges

echo "🚀 Starting SOV3 Jarvis..."

# Check if SSH tunnel is running
if ! curl -s --max-time 2 http://localhost:11436/api/tags >/dev/null 2>&1; then
    echo "🔐 Starting SSH tunnel to Vast.ai..."
    ssh -f -N -L 11436:localhost:11434 \
        -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -p 11353 root@ssh6.vast.ai
    sleep 2
else
    echo "✅ SSH tunnel already running"
fi

# Verify tunnel
if curl -s --max-time 5 http://localhost:11436/api/tags | grep -q "gemma4"; then
    echo "✅ Gemma 4 connected"
else
    echo "❌ Failed to connect to Gemma 4"
    exit 1
fi

# Change to project directory
cd ~/clawd/sovereign-temple

# Activate environment
source jarvis-env/bin/activate

# Check bridge status
echo "🌐 Checking bridges..."
python3 -c "
import sys
sys.path.insert(0, '.')
from sov3_bridge_network import get_bridge_network
from sov3_memory_hub import get_memory_hub
net = get_bridge_network()
hub = get_memory_hub()
print(f'  Bridges: {net.get_network_status()[\"network_status\"]}')
print(f'  Memory: {hub.stats()}')
"

echo ""
echo "🤖 Starting Jarvis..."
python voice_pipeline/jarvis_compass.py