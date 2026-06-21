#!/usr/bin/env python3
"""
Legion Trinity Supercluster Orchestrator
RTX 5090 (32GB) + RTX 8000x2 (46GB each) = 124GB VRAM
Routes tasks to optimal GPU based on load, VRAM, and role
"""
import json, time, asyncio, urllib.request, os
from pathlib import Path

GPU_FORGE  = "http://50.217.254.165:40408"   # RTX 8000 #1 — JARVIS/SOV3
GPU_ARCHIVE= "http://50.217.254.165:41600"   # RTX 8000 #2 — MEOK OS
GPU_SPEED  = None  # RTX 5090 — update when loaded

def call_ollama(base_url, prompt, model="qwen3.5:9b", max_tokens=2000):
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.3}
    }).encode()
    req = urllib.request.Request(f"{base_url}/api/generate", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read()).get("response", "")
    except Exception as e:
        return f"[ERROR: {e}]"

def embed(base_url, text, model="nomic-embed-text"):
    payload = json.dumps({"model": model, "prompt": text[:2000]}).encode()
    req = urllib.request.Request(f"{base_url}/api/embeddings", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("embedding", [])
    except:
        return []

def check_gpu(base_url):
    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=5) as r:
            d = json.loads(r.read())
            models = [m["name"] for m in d.get("models", [])]
            return {"online": True, "models": models}
    except:
        return {"online": False, "models": []}

def status():
    print("=== TRINITY GPU STATUS ===")
    for name, url in [("Forge (JARVIS/SOV3)", GPU_FORGE), ("Archive (MEOK OS)", GPU_ARCHIVE)]:
        s = check_gpu(url)
        icon = "✓" if s["online"] else "✗"
        models = ", ".join(s["models"][:3]) or "loading..."
        print(f"  {icon} {name}: {models}")
    print(f"  ⟳ Speed Demon (RTX 5090): still loading")

if __name__ == "__main__":
    status()
