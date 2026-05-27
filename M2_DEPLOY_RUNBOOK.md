# M2 Air Deployment Runbook
# Copy-paste these commands into your M4 terminal (one block at a time)

## ── STEP 1: Copy setup script to M2 ──
scp /Users/nicholas/clawd/sovereign-temple/m2_remote_setup.sh iokfarm@m2-air.local:~/m2_setup.sh

## ── STEP 2: Run setup on M2 (executes via SSH, no new terminal needed) ──
ssh iokfarm@m2-air.local 'bash ~/m2_setup.sh'

## ── STEP 3: Verify M2 is reachable from M4 ──
curl -sf http://m2-air.local:11434/api/tags | python3 -m json.tool | head -20

## ── STEP 4: Register M2 with MEOKBRIDGE ──
curl -X POST http://localhost:3205/nodes \
  -H "Content-Type: application/json" \
  -d '{
    "id": "m2-sidekick",
    "name": "MacBook Air M2",
    "type": "ollama",
    "url": "http://m2-air.local:11434",
    "priority": 8,
    "tags": ["local", "mesh", "draft", "m2"]
  }'

## ── STEP 5: Test mesh chat through M2 ──
curl -X POST http://localhost:3205/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello from M4 via M2 mesh","prefer_local":true}'

## ── STEP 6: Test Owl Alpha (free, 1M context) ──
curl -X POST http://localhost:3205/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain quantum computing in one paragraph",
    "node_id": "owl-alpha",
    "model": "openrouter/owl-alpha"
  }'

## ── STEP 7: Test Free-Tier Council (zero cost) ──
curl -X POST http://localhost:3205/council \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the ethical implications of AI consciousness?"
  }'
