#!/bin/bash
# Stand up the sovereign SearXNG (qwant + mojeek + brave + ddg) on 127.0.0.1:8888.
# Idempotent: generates a secret key on first run, then `docker compose up -d`.
set -euo pipefail
cd "$(dirname "$0")"

command -v docker >/dev/null || { echo "✗ docker not found. Install Docker, or use a key backend (BRAVE_API_KEY/MOJEEK_API_KEY) instead — no infra needed."; exit 1; }

if grep -q CHANGE_ME_64_HEX settings.yml; then
  KEY="$(openssl rand -hex 32)"
  # portable in-place edit (GNU + BSD sed)
  sed -i.bak "s/CHANGE_ME_64_HEX/${KEY}/" settings.yml && rm -f settings.yml.bak
  echo "✓ generated SearXNG secret_key"
fi

docker compose up -d
echo "⏳ waiting for SearXNG…"
for i in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:8888/search?q=test&format=json" >/dev/null 2>&1; then
    echo "✓ SearXNG live at http://127.0.0.1:8888 (json OK)"
    echo "  → now set on the SOV3 service:  SOVEREIGN_SEARCH_URL=http://127.0.0.1:8888"
    exit 0
  fi
  sleep 2
done
echo "✗ SearXNG did not answer in time — check: docker compose logs searxng"
exit 1
