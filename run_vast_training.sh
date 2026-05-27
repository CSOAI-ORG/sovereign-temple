#!/bin/bash
# 
# Sovereign Architecture v3 - Vast.ai Training Runner
# This script prepares and sends training to Vast.ai GPU
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/Users/nicholas/clawd/sovereign-temple"

echo "============================================"
echo "Sovereign Architecture v3 - Vast.ai Trainer"
echo "============================================"

# Check Vast.ai tunnel
echo ""
echo "Checking Vast.ai connection..."
if curl -s http://localhost:11436/v1/models > /dev/null 2>&1; then
    echo "✓ Vast.ai tunnel active (localhost:11436)"
    curl -s http://localhost:11436/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Available:', [m['id'] for m in d['data']])"
else
    echo "✗ Vast.ai tunnel not active"
    echo "Run: bash start-complete-sov3.sh"
    exit 1
fi

# Prepare model for training
echo ""
echo "Preparing training configuration..."

# Create training config
cat > "$PROJECT_DIR/train_config.json" << EOF
{
    "model": "sovereign_architecture_v3",
    "version": "ultimate",
    "vocab_size": 8000,
    "embed_dim": 512,
    "hidden_size": 512,
    "bottleneck_size": 64,
    "num_layers": 4,
    "seq_len": 128,
    "batch_size": 8,
    "learning_rate": 1e-4,
    "epochs": 20,
    "device": "cuda",
    "integrations": [
        "jarvis_recursive_feedback",
        "jarvis_non_euclidean_topology", 
        "jarvis_intentional_paradox",
        "nct_global_workspace",
        "nct_phi_calculator",
        "ouroboros_identity",
        "consciousness_ai_akorn",
        "consciousness_ai_affective",
        "mamba_ssm",
        "rwkv_linear_rnn"
    ],
    "metrics": [
        "phi",
        "self_attention", 
        "workspace_ignition",
        "valence",
        "arousal",
        "dominance"
    ]
}
EOF

echo "Training config saved to train_config.json"

# Check local GPU capability
echo ""
echo "Local system check:"
python3 -c "import torch; print('  PyTorch:', torch.__version__); print('  CUDA:', torch.cuda.is_available())"

# If local CUDA, train here
if python3 -c "import torch; torch.cuda.is_available()" 2>/dev/null; then
    echo ""
    echo "Local CUDA available - starting training..."
    cd "$PROJECT_DIR"
    python3 train_sovereign_v3.py
else
    echo ""
    echo "No local GPU - preparing for Vast.ai deployment..."
    
    # Export model architecture for remote training
    cd "$PROJECT_DIR"
    python3 -c "
import torch
from sovereign_architecture_v3 import SovereignArchitectureV3

model = SovereignArchitectureV3(
    vocab_size=8000,
    embed_dim=512, 
    hidden_size=512,
    bottleneck_size=64,
    num_layers=4
)

# Save architecture info
info = {
    'parameters': sum(p.numel() for p in model.parameters()),
    'layers': [
        'embedding',
        'feedback_layers (4xRecursiveFeedbackCell)', 
        'topology (NonEuclideanTopology)',
        'paradox (IntentionalParadox)',
        'workspace (GlobalWorkspace)',
        'phi_calculator (PhiCalculator)',
        'identity (OuroborosIdentity)',
        'oscillator (AKOrnOscillator)',
        'affective (AffectiveCore)',
        'ssm (SSMStateSpace)',
        'rwkv (RWKVCore)',
        'output'
    ],
    'device_requirements': 'cuda' 
}

import json
with open('model_architecture.json', 'w') as f:
    json.dump(info, f, indent=2)

print('Architecture exported to model_architecture.json')
print(f'Total parameters: {info[\"parameters\"]:,}')
"
    
    echo ""
    echo "============================================"
    echo "To train on Vast.ai:"
    echo "============================================"
    echo ""
    echo "1. SSH to Vast.ai instance:"
    echo "   ssh -p 11353 root@ssh6.vast.ai"
    echo ""
    echo "2. Copy files:"
    echo "   rsync -avz --progress $PROJECT_DIR/sovereign_architecture_v3.py root@ssh6.vast.ai:/workspace/"
    echo "   rsync -avz --progress $PROJECT_DIR/train_sovereign_v3.py root@ssh6.vast.ai:/workspace/"
    echo ""
    echo "3. Run training:"
    echo "   cd /workspace && python3 train_sovereign_v3.py"
    echo ""
    echo "Or use the quick trainer:"
    echo "   cd $PROJECT_DIR && python3 -c \""
    echo "   from train_sovereign_v3 import main; main()"
    echo "   \""
    echo ""
fi

echo ""
echo "✓ Setup complete!"
