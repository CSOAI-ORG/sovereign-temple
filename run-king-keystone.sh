#!/usr/bin/env bash
# ── King (SOV3) launch with keystone-sourced secrets ──────────────────────
# Built 2026-06-17. Drop-in replacement for the gunicorn command in the
# com.meok.sov3-gunicorn launchd plist. The 29 King secrets are injected from
# the keystone (GCP Secret Manager / Keychain); non-secret config (HOST, PORT,
# OLLAMA_*, etc.) still comes from .env, which gunicorn's app loads itself.
#
# To adopt on the NEXT clean SOV3 restart (do NOT force-restart a healthy King):
#   launchctl bootout gui/$(id -u)/com.meok.sov3-gunicorn   # only during maintenance
#   # point the plist ProgramArguments at this script, then:
#   launchctl kickstart -k gui/$(id -u)/com.meok.sov3-gunicorn
set -euo pipefail
cd /Users/nicholas/clawd/sovereign-temple
KEYSTONE="${KEYSTONE_BIN:-/Users/nicholas/clawd/keystone/keystone}"

# keystone run injects every stored secret as an env var, then exec's gunicorn.
# gunicorn's app still load_dotenv()s .env for non-secret runtime config.
exec "$KEYSTONE" run -- .venv/bin/python -m gunicorn sovereign-mcp-server:app \
  --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 127.0.0.1:3101 \
  --max-requests 1000 --max-requests-jitter 50 --timeout 120 --graceful-timeout 30 \
  --access-logfile /tmp/sov3-access.log --error-logfile /tmp/sov3-error.log --log-level info
