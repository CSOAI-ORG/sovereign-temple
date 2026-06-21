#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# COPY THIS TO M2 AND RUN IT THERE
# Fixes M4 IP and registers M2 in the mesh
# ═══════════════════════════════════════════════════════════════════════════════
echo "=== M4 CONNECTIVITY TEST ==="
ping -c 1 192.168.50.105 >/dev/null 2>&1 && echo "✅ M4 REACHABLE at 192.168.50.105" || echo "❌ M4 UNREACHABLE"

echo ""
echo "=== REGISTERING M2 WITH M4 MESH ==="
curl -sf -X POST http://192.168.50.105:3205/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "m2-sidekick",
    "name": "MacBook Air M2",
    "type": "ollama",
    "url": "http://192.168.50.176:11434",
    "priority": 8,
    "tags": ["local","mesh","draft","m2"]
  }' && echo "✅ M2 registered with M4 mesh" || echo "❌ Registration failed"

echo ""
echo "=== TEST MESH CHAT VIA M4 ==="
curl -sf -X POST http://192.168.50.105:3201/api/dual-brain \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello from M2 via M4 mesh"}' | head -c 200
