#!/usr/bin/env python3
"""
Penta-Mesh End-to-End Test
Tests all 5 nodes: Forge, Archive, Speed Demon, Dragon (M4), Edge (M2)
Usage: python test_penta.py [--quick]
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Add parent dir for node_config import
sys.path.insert(0, str(Path(__file__).parent))
from node_config import NODES

# Additional nodes (MacBooks)
LOCAL_NODES = {
    "dragon": {
        "name": "M4 Max — Dragon",
        "ollama": "http://localhost:11434",  # Local Ollama on M4
        "role": "Quantum + Local Inference",
    },
    "m2-edge": {
        "name": "M2 — Edge",
        "ollama": "http://100.64.0.5:11434",  # Tailscale IP if configured
        "role": "Edge / Offline Testing",
    }
}

API_GW = "http://50.217.254.165:41422"  # Archive port 6006 → external 41422
API_TOKEN = os.environ.get("LEGION_API_TOKEN", "legion-trinity-meok")


def test_ollama_node(name: str, ollama_url: str, timeout: int = 10) -> dict:
    start = time.time()
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=timeout) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
            latency = round((time.time() - start) * 1000)
            return {"status": "✓", "models": len(models), "latency_ms": latency,
                    "model_list": models[:3]}
    except Exception as e:
        return {"status": "✗", "error": str(e)[:60], "latency_ms": -1}


def test_api_gateway() -> dict:
    try:
        req = urllib.request.Request(
            f"{API_GW}/v1/health",
            headers={"Authorization": f"Bearer {API_TOKEN}"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            return {"status": "✓", "healthy_nodes": d.get("healthy_nodes", 0),
                    "total": d.get("total_nodes", 0)}
    except Exception as e:
        return {"status": "✗", "error": str(e)[:80]}


def test_inference(node_name: str, ollama_url: str) -> dict:
    payload = json.dumps({
        "model": "qwen3.5:9b",
        "prompt": "Reply in exactly 3 words: Legion is",
        "stream": False,
        "options": {"num_predict": 10, "temperature": 0}
    }).encode()
    try:
        start = time.time()
        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read()).get("response", "").strip()
            latency = round((time.time() - start) * 1000)
            return {"status": "✓", "response": result[:50], "latency_ms": latency}
    except Exception as e:
        return {"status": "✗", "error": str(e)[:60]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Skip inference tests")
    parser.add_argument("--task", default="health", help="Task type to test")
    parser.add_argument("--payload", default="{}", help="Task payload JSON")
    args = parser.parse_args()

    print("🐉 PENTA-MESH END-TO-END TEST")
    print(f"   API Gateway: {API_GW}")
    print()

    results = {}

    # Test GPU nodes (Trinity)
    print("── Trinity GPU Nodes ──────────────────")
    for node_key, node in NODES.items():
        ollama_url = f"http://{node['public_ip']}:{node.get('ollama_port','?')}" if node.get("ollama_port") else None
        if not ollama_url:
            print(f"  {node_key:12s} → ⟳ Loading (no port yet)")
            results[node_key] = {"status": "⟳"}
            continue

        r = test_ollama_node(node_key, ollama_url)
        status = r["status"]
        if r["latency_ms"] > 0:
            print(f"  {node_key:12s} → {status}  {r['models']} models  {r['latency_ms']}ms")
        else:
            print(f"  {node_key:12s} → {status}  {r.get('error','?')}")
        results[node_key] = r

    # Test local MacBook (Dragon)
    print("\n── MacBook Nodes ──────────────────────")
    r = test_ollama_node("dragon", LOCAL_NODES["dragon"]["ollama"], timeout=3)
    if r["status"] == "✓":
        print(f"  dragon       → {r['status']}  {r['models']} models  {r['latency_ms']}ms  [{', '.join(r.get('model_list',[])[:2])}]")
    else:
        print(f"  dragon       → {r['status']}  (local Ollama not running — `ollama serve` to start)")
    results["dragon"] = r

    # Test API Gateway
    print("\n── API Gateway ────────────────────────")
    gw = test_api_gateway()
    print(f"  gateway      → {gw['status']}  {gw.get('healthy_nodes','?')}/{gw.get('total','?')} nodes healthy")
    results["gateway"] = gw

    # Inference tests (unless --quick)
    if not args.quick:
        print("\n── Inference Tests ────────────────────")
        for node_key, node in NODES.items():
            if node.get("status") != "running" or not node.get("ollama_port"):
                continue
            ollama_url = f"http://{node['public_ip']}:{node['ollama_port']}"
            r = test_inference(node_key, ollama_url)
            print(f"  {node_key:12s} → {r['status']}  \"{r.get('response','?')}\"  {r.get('latency_ms',-1)}ms")

    # Summary
    healthy = sum(1 for r in results.values() if r.get("status") == "✓")
    total = len(results)
    print(f"\n{'='*42}")
    print(f"  {healthy}/{total} nodes healthy")

    if healthy >= 3:
        print("  ✅ Penta-Mesh OPERATIONAL")
    elif healthy >= 2:
        print("  ⚠️  Partial — core online but check failures")
    else:
        print("  ❌ Critical — fewer than 2 nodes responding")

    return 0 if healthy >= 2 else 1


if __name__ == "__main__":
    sys.exit(main())
