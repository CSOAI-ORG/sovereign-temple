#!/bin/bash
# Run this on M2 to fix M4 connectivity
# M4 IP: 192.168.50.105

echo "=== Testing M4 connectivity ==="
ping -c 1 192.168.50.105 && echo "M4 REACHABLE" || echo "M4 UNREACHABLE"

echo ""
echo "=== SSH to M4 (if key-based auth is set up) ==="
# ssh -o ConnectTimeout=5 nicholas@192.168.50.105 'echo M4_OK'

echo ""
echo "=== Register M2 with M4 mesh ==="
curl -sf -X POST http://192.168.50.105:3205/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "m2-sidekick",
    "name": "MacBook Air M2",
    "type": "ollama",
    "url": "http://192.168.50.176:11434",
    "priority": 8,
    "tags": ["local","mesh","draft","m2"]
  }' && echo "M2 registered with M4" || echo "Registration failed"
