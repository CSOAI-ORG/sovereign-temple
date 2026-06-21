#!/bin/bash
# Dragon Sovereign Council — Node Setup Script
# Run on Host 32241 (48GB VRAM + 192GB RAM) after renting
# Usage: bash setup_dragon_node.sh

set -e
echo "🐉 Dragon Sovereign Council — Node Setup"

# 1. System deps
apt-get update -qq && apt-get install -y git curl python3-pip docker.io docker-compose >/dev/null 2>&1
echo "  ✓ System deps installed"

# 2. Create model directories
mkdir -p /models/{jarvis,forge,archive,edge}
echo "  ✓ Model directories created"

# 3. Install HuggingFace CLI
pip install huggingface-hub -q
echo "  ✓ HuggingFace CLI ready"

# 4. Download models in parallel (~40GB total)
echo "  Downloading 4 models (parallel, ~40GB)..."
echo "  This takes 10-20 minutes..."

# 3× Qwen2.5-14B-AWQ (~13GB each) + 1× Qwen2.5-7B-AWQ (~4GB)
huggingface-cli download Qwen/Qwen2.5-14B-Instruct-AWQ --local-dir /models/jarvis --local-dir-use-symlinks False &
PID_J=$!
huggingface-cli download deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct --local-dir /models/forge --local-dir-use-symlinks False &
PID_F=$!
huggingface-cli download Qwen/Qwen2.5-14B-Instruct-AWQ --local-dir /models/archive --local-dir-use-symlinks False &
PID_A=$!
huggingface-cli download Qwen/Qwen2.5-7B-Instruct-AWQ --local-dir /models/edge --local-dir-use-symlinks False &
PID_E=$!

wait $PID_J && echo "  ✓ Jarvis (14B) downloaded"
wait $PID_F && echo "  ✓ Forge (Coder) downloaded"
wait $PID_A && echo "  ✓ Archive (14B) downloaded"
wait $PID_E && echo "  ✓ Edge (7B) downloaded"

# 5. Copy docker-compose configs
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp "$SCRIPT_DIR/dragon-council.yml" /root/
cp "$SCRIPT_DIR/nginx-council.conf" /root/
mkdir -p /root/council-chamber
cp "$SCRIPT_DIR/council-chamber/democratic_engine.py" /root/council-chamber/
cp "$SCRIPT_DIR/council-chamber/Dockerfile" /root/council-chamber/

# Create prometheus config
cat > /root/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'dragon-council'
    static_configs:
      - targets: ['council-chamber:8090', 'jarvis:8001', 'forge:8002', 'archive:8003', 'edge:8004']
EOF

mkdir -p /root/council-state

# 6. Launch Dragon Council
cd /root
docker-compose -f dragon-council.yml up -d --build
echo ""
echo "  Waiting for models to load (~3 minutes)..."
sleep 180

# 7. Verify
echo ""
echo "✅ Dragon Council Status:"
curl -s http://localhost:8090/v1/council/status | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'  Quorum: {d[\"quorum\"]}')
for name, status in d['councillors'].items():
    print(f'  {name:8s}: {status[\"status\"]}')
" 2>/dev/null || echo "  Chamber starting up..."

echo ""
echo "🐉 Dragon Council LIVE"
echo "  Chamber API:  http://localhost:8090/v1/council/deliberate"
echo "  Fast Edge:    http://localhost:80/v1/fast/"
echo "  Code Forge:   http://localhost:80/v1/code/"
echo "  Dashboard:    http://localhost:3000 (dragon2026)"
echo "  Grafana:      http://localhost:3000"
echo ""
echo "Test: curl -X POST http://localhost:8090/v1/council/deliberate -H 'Content-Type: application/json' -d '{\"query\": \"What is 2+2?\", \"fast\": true}'"
