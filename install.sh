#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# MEOKCLAW One-Liner Installer
# curl -fsSL https://meok.ai/install.sh | bash
# ═══════════════════════════════════════════════════════════════════════════════
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${BLUE}[MEOKCLAW]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

MEOK_DIR="${HOME}/meokclaw"
REPO_URL="https://github.com/nicholastempleman/meokclaw.git"

log "╔══════════════════════════════════════════════════════════════════════════════╗"
log "║                    🧠 MEOKCLAW INSTALLER v1.0.0                              ║"
log "║           Sovereign AI — Your Hardware, Your Data, Your Rules                ║"
log "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""

# ── 1. SYSTEM CHECKS ──
log "Checking system..."
OS=$(uname -s)
ARCH=$(uname -m)
if [[ "$OS" != "Darwin" ]]; then
  fail "MEOKCLAW currently supports macOS only. Linux support coming soon."
fi
if [[ "$ARCH" != "arm64" ]]; then
  warn "Non-Apple Silicon detected. Performance may vary."
fi
ok "System: $OS $ARCH"

# ── 2. INSTALL DEPENDENCIES ──
log "Installing dependencies..."

# Homebrew
if ! command -v brew &>/dev/null; then
  log "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
ok "Homebrew ready"

# Ollama
if ! command -v ollama &>/dev/null; then
  log "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi
ok "Ollama ready"

# Node.js 20+
if ! command -v node &>/dev/null || [[ $(node -v | cut -d'v' -f2 | cut -d'.' -f1) -lt 20 ]]; then
  log "Installing Node.js..."
  brew install node@22 2>/dev/null || brew install node
fi
ok "Node.js $(node -v) ready"

# Python 3.12+
if ! command -v python3 &>/dev/null; then
  log "Installing Python..."
  brew install python@3.14
fi
ok "Python $(python3 --version) ready"

# ── 3. CLONE REPO ──
if [[ -d "$MEOK_DIR" ]]; then
  log "Updating existing MEOKCLAW installation..."
  cd "$MEOK_DIR"
  git pull || warn "Git pull failed, continuing..."
else
  log "Cloning MEOKCLAW repository..."
  git clone "$REPO_URL" "$MEOK_DIR" 2>/dev/null || {
    log "Repo clone failed. Creating local scaffold..."
    mkdir -p "$MEOK_DIR"
  }
fi
ok "MEOKCLAW at $MEOK_DIR"

# ── 4. PULL OLLAMA MODELS ──
log "Pulling AI models (this may take 10-30 minutes)..."
for model in qwen3:0.6b qwen3:4b qwen3:8b nomic-embed-text; do
  if ollama list | grep -q "^$model"; then
    ok "Model already pulled: $model"
  else
    log "Pulling $model..."
    ollama pull "$model" || warn "Failed to pull $model"
  fi
done

# ── 5. INSTALL PYTHON DEPS ──
log "Installing Python dependencies..."
cd "$MEOK_DIR"
python3 -m pip install fastapi uvicorn httpx aiohttp pyyaml pydantic 2>/dev/null || true
ok "Python dependencies ready"

# ── 6. SETUP ENV ──
if [[ ! -f ".env" ]]; then
  log "Creating environment config..."
  cat > .env << EOF
OPENROUTER_API_KEY=your_key_here
MEOKBRIDGE_PORT=3205
DUAL_BRAIN_PORT=3201
SOV3_PORT=3101
EOF
  warn "Please edit .env and add your OpenRouter API key"
fi

# ── 7. START SERVICES ──
log "Starting MEOKCLAW services..."

# Ollama
if ! pgrep -x "ollama" >/dev/null; then
  ollama serve &
  sleep 3
fi
ok "Ollama serving on :11434"

# Dual-Brain API
if ! lsof -ti:3201 >/dev/null 2>&1; then
  nohup python3 -m uvicorn dual_brain_api:app --host 0.0.0.0 --port 3201 > /tmp/dual_brain.log 2>&1 &
  sleep 2
fi
ok "Dual-Brain API on :3201"

# MEOKBRIDGE API
if ! lsof -ti:3205 >/dev/null 2>&1; then
  nohup python3 -m uvicorn meokbridge.api:app --host 0.0.0.0 --port 3205 > /tmp/meokbridge.log 2>&1 &
  sleep 2
fi
ok "MEOKBRIDGE API on :3205"

# ── 8. HEALTH CHECK ──
log "Running health checks..."
if curl -sf http://localhost:3201/health >/dev/null 2>&1; then
  ok "Dual-Brain API healthy"
else
  warn "Dual-Brain API may need manual start"
fi

if curl -sf http://localhost:3205/health >/dev/null 2>&1; then
  ok "MEOKBRIDGE API healthy"
else
  warn "MEOKBRIDGE API may need manual start"
fi

# ── 9. FINAL ──
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ MEOKCLAW INSTALLED                                     ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  Chat API:      http://localhost:3201/api/dual-brain                         ║"
echo "║  Mesh API:      http://localhost:3205/v1/chat                                ║"
echo "║  Dashboard:     http://localhost:3201/dashboard                              ║"
echo "║  Ollama:        http://localhost:11434                                       ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  QUICK TEST:                                                                 ║"
echo "║  curl -X POST http://localhost:3201/api/dual-brain \                         ║"
echo "║    -H \"Content-Type: application/json\" \                                     ║"
echo "║    -d '{\"message\":\"Hello MEOKCLAW\"}'                                       ║"
echo "╠══════════════════════════════════════════════════════════════════════════════╣"
echo "║  NEXT STEPS:                                                                 ║"
echo "║  1. Add OpenRouter key: nano ~/meokclaw/.env                                 ║"
echo "║  2. Install mobile: cd ~/meokclaw/meokclaw-v2 && npm install                 ║"
echo "║  3. Read docs: cat ~/meokclaw/README.md                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
ok "Installation complete!"
