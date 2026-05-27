#!/bin/bash
# MEOK LABS — Sovereign Stack Bootstrap
# Installs verified open-source tools for the sovereign AI empire
# Run on: M2/M4 MacBook or Legion GPU nodes
# All tools verified as real and installable (April 2026)

set -e

PYTHON="/opt/homebrew/bin/python3.11"
MEOK_ROOT="${MEOK_ROOT:-/Users/nicholas/clawd}"
STACK_DIR="$MEOK_ROOT/sovereign-temple/legion-omega/stack"

echo "🐉 MEOK LABS SOVEREIGN STACK BOOTSTRAP"
echo "======================================="
echo "Python: $PYTHON"
echo "Stack dir: $STACK_DIR"
echo ""

mkdir -p "$STACK_DIR"
cd "$STACK_DIR"

# ── 1. Agno — 10,000x faster agent runtime ──────────────────────────────────
echo "[1/6] Installing agno (fast agent framework)..."
$PYTHON -m pip install agno --quiet
$PYTHON -c "import agno; print('  ✅ agno', agno.__version__)"

# ── 2. inspect-ai — UK AISI safety evaluation ───────────────────────────────
echo "[2/6] Verifying inspect-ai..."
$PYTHON -c "import inspect_ai; print('  ✅ inspect-ai', inspect_ai.__version__)"

# ── 3. PennyLane — quantum-classical hybrid AI ──────────────────────────────
echo "[3/6] Installing pennylane..."
$PYTHON -m pip install pennylane pennylane-lightning --quiet
$PYTHON -c "import pennylane; print('  ✅ pennylane', pennylane.__version__)"

# ── 4. AgentNeo — multi-agent observability ─────────────────────────────────
echo "[4/6] Installing agentneo..."
$PYTHON -m pip install agentneo --quiet
echo "  ✅ agentneo installed"

# ── 5. A-Evolve — self-rewriting agent DNA ──────────────────────────────────
echo "[5/6] Cloning A-Evolve..."
if [ ! -d "$STACK_DIR/a-evolve" ]; then
    git clone --depth 1 https://github.com/A-EVO-Lab/a-evolve.git "$STACK_DIR/a-evolve"
    cd "$STACK_DIR/a-evolve" && $PYTHON -m pip install -e . --quiet && cd "$STACK_DIR"
    echo "  ✅ A-Evolve cloned and installed"
else
    echo "  ✅ A-Evolve already present"
fi

# ── 6. Genesis — physics engine for embodied AI ─────────────────────────────
echo "[6/6] Cloning Genesis physics engine..."
if [ ! -d "$STACK_DIR/genesis" ]; then
    git clone --depth 1 https://github.com/Genesis-Embodied-AI/Genesis.git "$STACK_DIR/genesis"
    echo "  ✅ Genesis cloned (install separately — requires CUDA/Metal)"
    echo "  To install: cd $STACK_DIR/genesis && pip install -e ."
else
    echo "  ✅ Genesis already present"
fi

echo ""
echo "🔥 STACK READY"
echo ""
echo "Installed:"
echo "  agno 2.5.14       — agent runtime"
echo "  inspect-ai 0.3.x  — CSOAI safety evaluation"
echo "  pennylane         — quantum AI layer"
echo "  agentneo          — observability dashboard"
echo "  a-evolve          — self-rewriting agent DNA"
echo "  genesis           — physics simulation (manual install needed)"
echo ""
echo "Start AgentNeo dashboard:  agentneo launch"
echo "Run CSOAI evaluation:      cd $MEOK_ROOT/meok && /opt/homebrew/bin/python3.11 -m inspect_ai eval tests/csoai_care_membrane_eval.py::csoai_care_membrane_bypass --model ollama/qwen2.5:35b"
echo "Start stack_eval:          cd $MEOK_ROOT/sovereign-temple/legion-omega && python3 scripts/real_work_loop.py --project stack_eval --task code"
