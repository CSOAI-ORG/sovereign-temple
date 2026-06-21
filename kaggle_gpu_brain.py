#!/usr/bin/env python3
"""
Kaggle GPU Brain — Remote Gemma 4 26B for Jarvis/Sophie
=========================================================
Run this in a Kaggle notebook with dual T4 GPUs (free, 30hr/week).
Exposes an OpenAI-compatible API that Jarvis can call from home.

Setup in Kaggle:
1. New Notebook → Settings → Accelerator → GPU T4 x2
2. Paste this entire file into a cell
3. Run it — ngrok creates a public URL
4. Copy the URL back to your .env as KAGGLE_GPU_URL

Architecture:
  Kaggle T4x2 (32GB VRAM) → Gemma 4 26B Q4 → OpenAI-compatible API → ngrok tunnel
  Jarvis at home → calls the tunnel URL → gets 26B quality responses
"""

# Install dependencies (run in first Kaggle cell)
SETUP_COMMANDS = """
!pip install -q vllm ngrok fastapi uvicorn
!pip install -q huggingface_hub
"""

# The actual server code (run in second cell)
SERVER_CODE = '''
import os
import subprocess
import threading
import time
import requests

# === CONFIG ===
MODEL = "google/gemma-2-27b-it"  # Or gemma-4-26b when available on HF
QUANTIZATION = "awq"  # 4-bit quantization to fit in 32GB
MAX_MODEL_LEN = 8192
NGROK_TOKEN = os.environ.get("NGROK_TOKEN", "")  # Set in Kaggle secrets

# === START VLLM SERVER ===
def start_vllm():
    """Start vLLM with OpenAI-compatible API."""
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL,
        "--quantization", QUANTIZATION,
        "--max-model-len", str(MAX_MODEL_LEN),
        "--tensor-parallel-size", "2",  # Use both T4s
        "--host", "0.0.0.0",
        "--port", "8000",
        "--trust-remote-code",
    ]
    subprocess.Popen(cmd)

# === START NGROK TUNNEL ===
def start_ngrok():
    """Create public tunnel so Jarvis can reach this from home."""
    import ngrok
    if NGROK_TOKEN:
        ngrok.set_auth_token(NGROK_TOKEN)
    listener = ngrok.forward(8000, authtoken=NGROK_TOKEN)
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  🧠 KAGGLE GPU BRAIN — ONLINE                           ║
║                                                          ║
║  Model: {MODEL}
║  VRAM:  32GB (T4 x2, tensor parallel)                   ║
║  Quant: {QUANTIZATION}
║                                                          ║
║  PUBLIC URL: {listener.url()}
║                                                          ║
║  Add to .env:                                            ║
║  KAGGLE_GPU_URL={listener.url()}
║                                                          ║
║  Test:                                                   ║
║  curl {listener.url()}/v1/models
╚══════════════════════════════════════════════════════════╝
""")
    return listener

# === LAUNCH ===
print("Starting vLLM server...")
start_vllm()

print("Waiting for server to load model...")
for i in range(120):
    try:
        r = requests.get("http://localhost:8000/v1/models", timeout=2)
        if r.status_code == 200:
            print(f"✅ Model loaded in {i*5}s")
            break
    except:
        pass
    time.sleep(5)

print("Starting ngrok tunnel...")
listener = start_ngrok()

# Keep alive
print("\\n🟢 GPU Brain running. Keep this notebook open.")
print("   Jarvis can now use 26B quality from home.")
while True:
    time.sleep(60)
'''

# === LOCAL INTEGRATION ===
# Add this to jarvis_compass.py to use the Kaggle GPU brain

JARVIS_INTEGRATION = '''
# In call_cloud_llm(), add before the cloud providers loop:
KAGGLE_GPU_URL = os.environ.get("KAGGLE_GPU_URL", "")
if KAGGLE_GPU_URL:
    try:
        resp = requests.post(
            f"{KAGGLE_GPU_URL}/v1/chat/completions",
            json={
                "model": "google/gemma-2-27b-it",
                "messages": messages[-10:],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=30,
        )
        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            reply = choices[0].get("message", {}).get("content", "")
            if reply:
                return (reply, "Kaggle-GPU-26B")
    except Exception as e:
        log.warning(f"🖥️ Kaggle GPU brain unavailable: {e}")
'''


if __name__ == "__main__":
    print("=" * 60)
    print("  Kaggle GPU Brain Setup")
    print("=" * 60)
    print()
    print("1. Go to kaggle.com → New Notebook")
    print("2. Settings → Accelerator → GPU T4 x2")
    print("3. Add NGROK_TOKEN to Kaggle Secrets")
    print("   (Get free token at ngrok.com)")
    print()
    print("4. Cell 1 — paste and run:")
    print(SETUP_COMMANDS)
    print()
    print("5. Cell 2 — paste and run:")
    print("   (The SERVER_CODE from this file)")
    print()
    print("6. Copy the PUBLIC URL and add to .env:")
    print("   KAGGLE_GPU_URL=https://xxxx.ngrok.io")
    print()
    print("7. Restart Jarvis — it will use the 26B brain")
    print()
    print("=" * 60)
    print()
    print("To integrate with Jarvis, add this to jarvis_compass.py:")
    print(JARVIS_INTEGRATION)
