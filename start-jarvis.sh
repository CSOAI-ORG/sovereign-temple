#!/bin/bash
# JARVIS Launch Script — uses jarvis-env venv with all deps
# Run: ./start-jarvis.sh

set -e

ENV_DIR="/Users/nicholas/clawd/sovereign-temple/jarvis-env"
COMPASS="/Users/nicholas/clawd/sovereign-temple/voice_pipeline/jarvis_compass.py"

if [ ! -d "$ENV_DIR" ]; then
    echo "❌ jarvis-env not found. Create it first:"
    echo "   python3.11 -m venv $ENV_DIR"
    echo "   $ENV_DIR/bin/pip install sounddevice openwakeword silero-vad lightning-whisper-mlx mlx-audio kokoro-mlx pyaudio numpy requests tenacity torch torchaudio"
    exit 1
fi

echo "🤖 Starting JARVIS v2.0 — Sovereign AI Assistant"
echo "   Environment: jarvis-env (Python 3.11)"
echo "   Brains: Qwen 9B/35B (GPU) + Nemotron + DeepSeek + MiniMax + Vision"
echo "   TTS: Kokoro-82M (streaming)"
echo "   Press ENTER to interrupt | Say 'goodbye' to stop"
echo ""

exec "$ENV_DIR/bin/python3" "$COMPASS"
