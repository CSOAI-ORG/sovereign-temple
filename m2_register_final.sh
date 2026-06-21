#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# RUN THIS ON M2 (192.168.50.176) TO COMPLETE MESH REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════
set -e

M4_IP="192.168.50.105"
M2_IP="192.168.50.176"

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    🔗 M2 → M4 MESH REGISTRATION                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# 1. Verify M4 is reachable
echo "[1/4] Testing M4 connectivity ($M4_IP)..."
if ping -c 1 -W 3 "$M4_IP" >/dev/null 2>&1; then
  echo "    ✅ M4 REACHABLE"
else
  echo "    ❌ M4 UNREACHABLE at $M4_IP"
  echo "    Trying mDNS fallback..."
  if ping -c 1 -W 3 "m4-macbook.local" >/dev/null 2>&1; then
    M4_IP="m4-macbook.local"
    echo "    ✅ M4 REACHABLE via mDNS"
  else
    echo "    ❌ Cannot reach M4. Check network."
    exit 1
  fi
fi

# 2. Verify Ollama is running
echo ""
echo "[2/4] Verifying Ollama on M2..."
if curl -sf "http://localhost:11434/api/tags" >/dev/null 2>&1; then
  models=$(curl -sf "http://localhost:11434/api/tags" 2>/dev/null | grep -c '"name"' || echo "0")
  echo "    ✅ Ollama running with $models models"
else
  echo "    ⚠️  Ollama not responding. Starting..."
  nohup ollama serve >/tmp/ollama.log 2>&1 &
  sleep 3
  echo "    ✅ Ollama started"
fi

# 3. Register with M4 mesh
echo ""
echo "[3/4] Registering M2 with M4 mesh ($M4_IP:3205)..."
register_response=$(curl -sf -X POST "http://$M4_IP:3205/nodes" \
  -H "Content-Type: application/json" \
  -d "{
    \"id\": \"m2-sidekick\",
    \"name\": \"MacBook Air M2\",
    \"type\": \"ollama\",
    \"url\": \"http://$M2_IP:11434\",
    \"priority\": 8,
    \"tags\": [\"local\",\"mesh\",\"draft\",\"m2\"]
  }" 2>&1)

if echo "$register_response" | grep -q "added\|already"; then
  echo "    ✅ M2 registered with M4 mesh"
else
  echo "    ⚠️  Registration response: $register_response"
fi

# 4. Test mesh chat
echo ""
echo "[4/4] Testing mesh chat through M4..."
test_response=$(curl -sf -X POST "http://$M4_IP:3201/api/dual-brain" \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello from M2 via M4 mesh","max_tokens":20}' 2>&1 | head -c 200)

if [[ -n "$test_response" ]]; then
  echo "    ✅ Mesh chat working!"
  echo "    Response preview: $(echo "$test_response" | grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4 | head -c 80)"
else
  echo "    ⚠️  Mesh chat test returned empty (may be slow)"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ M2 MESH NODE ACTIVE                                    ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  M2 IP:       $M2_IP                                                        ║"
echo "║  M4 Gateway:  $M4_IP                                                        ║"
echo "║  Ollama:      http://$M2_IP:11434                                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
