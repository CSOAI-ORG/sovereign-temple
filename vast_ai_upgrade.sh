#!/bin/bash
# Vast.ai Upgrade Script — Provision a bigger GPU instance
# Run this after renting a 24GB+ VRAM instance on vast.ai

set -e

INSTANCE_IP="${1:-IP_HERE}"
INSTANCE_PORT="${2:-PORT_HERE}"
LOCAL_PORT=11437

if [ "$INSTANCE_IP" = "IP_HERE" ]; then
    echo "Usage: ./vast_ai_upgrade.sh <instance_ip> <ssh_port>"
    echo ""
    echo "1. Go to https://vast.ai and rent an instance with:"
    echo "   - GPU: RTX 3090 / RTX 4090 / RTX A5000 (24GB+ VRAM)"
    echo "   - Disk: 50GB+"
    echo "   - Image: pytorch or cuda"
    echo ""
    echo "2. Copy the SSH command from Vast.ai dashboard"
    echo "3. Run this script with the IP and port"
    exit 1
fi

echo "🚀 Setting up Vast.ai instance at $INSTANCE_IP:$INSTANCE_PORT"

# SSH into instance and set up Ollama + models
ssh -o StrictHostKeyChecking=no -p "$INSTANCE_PORT" "root@$INSTANCE_IP" << 'REMOTE'
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh

    # Start Ollama in background
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3

    # Pull premium models
    echo "📦 Pulling gemma3:12b (~8GB)..."
    ollama pull gemma3:12b

    echo "📦 Pulling qwen3:8b (~5GB)..."
    ollama pull qwen3:8b

    echo "📦 Pulling llama3.1:8b (~5GB)..."
    ollama pull llama3.1:8b

    # Verify
    ollama list
    echo "✅ Setup complete"
REMOTE

# Set up local tunnel
echo "🔗 Creating SSH tunnel localhost:$LOCAL_PORT → $INSTANCE_IP:11434"
ssh -f -N -L $LOCAL_PORT:localhost:11434 \
    -o StrictHostKeyChecking=no \
    -o ServerAliveInterval=30 \
    -o ExitOnForwardFailure=yes \
    -p "$INSTANCE_PORT" "root@$INSTANCE_IP"

echo "✅ Tunnel active on localhost:$LOCAL_PORT"
echo ""
echo "Update your dual_brain_router.py models config:"
cat << 'CONFIG'
    "gemma3-12b-vast": {
        "id": "gemma3:12b",
        "provider": "ollama",
        "base_url": "http://localhost:11437",
        "hemisphere": Hemisphere.BOTH,
        "cost_in": 0,
        "cost_out": 0,
        "typical_latency_ms": 3000,
        "strengths": ["coding", "reasoning", "vision", "long_context", "gpu"],
        "max_tokens": 128000,
    },
    "qwen3-8b-vast": {
        "id": "qwen3:8b",
        "provider": "ollama",
        "base_url": "http://localhost:11437",
        "hemisphere": Hemisphere.LEFT,
        "cost_in": 0,
        "cost_out": 0,
        "typical_latency_ms": 2500,
        "strengths": ["coding", "fast", "gpu"],
        "max_tokens": 32768,
    },
CONFIG

echo ""
echo "Test: curl http://localhost:$LOCAL_PORT/api/tags"
