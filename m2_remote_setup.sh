#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# M2 AIR SETUP — Run this on your MacBook Air M2
# Copy: scp m2_remote_setup.sh iokfarm@m2-air.local:~/
# Run:  ssh iokfarm@m2-air.local 'bash ~/m2_remote_setup.sh'
# ═══════════════════════════════════════════════════════════════════════════════
set -e

log()  { echo "[M2-SETUP] $1"; }

log "Setting up M2 Air as MEOKBRIDGE mesh node..."

# Check Ollama
if ! command -v ollama &>/dev/null; then
  log "Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
fi
echo "[OK] Ollama installed"

# Pull lightweight models for M2 8GB
log "Pulling M2-optimized models..."
for model in qwen3:0.6b qwen3:1.8b qwen3:4b nomic-embed-text; do
  ollama pull "$model" || echo "[WARN] Failed: $model"
done
echo "[OK] Models pulled"

# Start Ollama
log "Starting Ollama..."
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 3
echo "[OK] Ollama serving on port 11434"

# Show status
log "M2 Status:"
echo "  Models: $(ollama list 2>/dev/null | wc -l)"
echo "  RAM: $(sysctl -n hw.memsize 2>/dev/null | awk '{print $1/1024/1024/1024 " GB"}')"
echo "  CPU: $(sysctl -n machdep.cpu.brand_string 2>/dev/null)"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              ✅ M2 SETUP COMPLETE                              ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Ollama:    http://m2-air.local:11434                          ║"
echo "║  Models:    qwen3:0.6b, qwen3:1.8b, qwen3:4b, nomic-embed-text ║"
echo "║  Discovery: m2-air.local (Bonjour/mDNS)                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
