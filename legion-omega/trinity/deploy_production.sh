#!/bin/bash
# Legion Trinity — Production Deployment
# Deploys: API Gateway + Heartbeat + Redis (auth) + Models
# Run from your Mac: bash deploy_production.sh

set -e

FORGE_IP="50.217.254.165"
FORGE_SSH=41724
ARCHIVE_IP="50.217.254.165"
ARCHIVE_SSH=41620
TRINITY_DIR="/root/legion"
API_TOKEN="${LEGION_API_TOKEN:-legion-trinity-meok}"

echo "🐉 LEGION TRINITY — Production Deployment"
echo "  Forge:   ssh -p $FORGE_SSH root@$FORGE_IP"
echo "  Archive: ssh -p $ARCHIVE_SSH root@$ARCHIVE_IP"
echo ""

forge_ssh() { ssh -o StrictHostKeyChecking=no -p $FORGE_SSH root@$FORGE_IP "$@"; }
archive_ssh() { ssh -o StrictHostKeyChecking=no -p $ARCHIVE_SSH root@$ARCHIVE_IP "$@"; }
forge_scp() { scp -o StrictHostKeyChecking=no -P $FORGE_SSH "$1" root@$FORGE_IP:"$2"; }
archive_scp() { scp -o StrictHostKeyChecking=no -P $ARCHIVE_SSH "$1" root@$ARCHIVE_IP:"$2"; }

echo "### Step 1: Create legion dirs on both nodes"
forge_ssh "mkdir -p $TRINITY_DIR"
archive_ssh "mkdir -p $TRINITY_DIR"

echo "### Step 2: Copy trinity files to both nodes"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
for f in node_config.py api_gateway.py heartbeat.py; do
    forge_scp "$SCRIPT_DIR/$f" "$TRINITY_DIR/$f"
    archive_scp "$SCRIPT_DIR/$f" "$TRINITY_DIR/$f"
done

echo "### Step 3: Install Python deps on both nodes"
DEPS="fastapi uvicorn pydantic"
forge_ssh "pip install $DEPS -q"
archive_ssh "pip install $DEPS -q"

echo "### Step 4: Set Redis password on Forge"
forge_ssh "redis-cli config set requirepass '$API_TOKEN' 2>/dev/null || echo 'Redis not running — start manually'"

echo "### Step 5: Start API Gateway on Archive (port 8080)"
archive_ssh "pkill -f api_gateway.py 2>/dev/null; cd $TRINITY_DIR && nohup python3 api_gateway.py > /var/log/api_gateway.log 2>&1 &"
sleep 3
HEALTH=$(archive_ssh "curl -s http://localhost:8080/v1/health 2>/dev/null | head -100" 2>/dev/null || echo "starting...")
echo "  API Gateway: $HEALTH"

echo "### Step 6: Start Heartbeat on Forge (systemd)"
# Write systemd service
forge_ssh "cat > /etc/systemd/system/legion-heartbeat.service << 'EOF'
[Unit]
Description=Legion Self-Improving Heartbeat
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$TRINITY_DIR
Environment=FORGE_OLLAMA=http://localhost:11434
Environment=ARCHIVE_OLLAMA=http://50.217.254.165:41600
ExecStart=/usr/bin/python3 $TRINITY_DIR/heartbeat.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

forge_ssh "systemctl daemon-reload && systemctl enable legion-heartbeat && systemctl restart legion-heartbeat"
sleep 2
HBEAT=$(forge_ssh "systemctl is-active legion-heartbeat" 2>/dev/null || echo "unknown")
echo "  Heartbeat service: $HBEAT"

echo ""
echo "✅ Legion Trinity Production Deployment Complete"
echo ""
echo "  API Gateway:    http://$ARCHIVE_IP:41600 → port 8080"
echo "  Archive Ollama: http://$ARCHIVE_IP:41600"
echo "  Forge Ollama:   http://$FORGE_IP:40408"
echo ""
echo "  Test: curl -H 'Authorization: Bearer $API_TOKEN' http://$ARCHIVE_IP:8080/v1/health"
echo "  Logs: ssh -p $ARCHIVE_SSH root@$ARCHIVE_IP 'tail -f /var/log/api_gateway.log'"
echo "  Beat: ssh -p $FORGE_SSH root@$FORGE_IP 'journalctl -u legion-heartbeat -f'"
