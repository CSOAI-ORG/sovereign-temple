#!/usr/bin/env python3
"""
Legion Omega — One-Command Deployment
MEOK AI Labs
Usage: python deploy.py [--mode full|edge|cloud|local]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(cmd, **kwargs):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def check_gpu():
    try:
        run(["nvidia-smi"], capture_output=True)
        print("[GPU] NVIDIA detected")
        return True
    except Exception:
        print("[GPU] No NVIDIA GPU — using CPU/Vast.ai")
        return False


def check_vast_gpu():
    import urllib.request
    try:
        with urllib.request.urlopen("http://50.217.254.165:40408/api/tags", timeout=5) as r:
            data = json.loads(r.read())
            models = [m["name"] for m in data.get("models", [])]
            print(f"[Vast.ai] GPU online: {models}")
            return True
    except Exception:
        print("[Vast.ai] GPU unreachable")
        return False


def generate_env():
    env = ROOT / ".env"
    if env.exists():
        print("[ENV] .env already exists")
        return
    content = f"""ANTHROPIC_API_KEY={os.environ.get('ANTHROPIC_API_KEY', '')}
REDIS_URL=redis://localhost:6379
VAST_OLLAMA_URL=http://50.217.254.165:40408
AGENT_COUNT=47
NODES_PER_AGENT=33
GVU_SAFETY=strict
POWER_BUDGET=20
"""
    env.write_text(content)
    print("[ENV] Generated .env")


def deploy_local():
    """Run without Docker — useful for dev"""
    print("[LOCAL] Starting Redis...")
    subprocess.Popen(["redis-server", "--daemonize", "yes"])

    print("[LOCAL] Starting swarm orchestrator...")
    os.chdir(ROOT)

    print("[LOCAL] Starting dashboard...")
    print("  Run manually: streamlit run ui/dashboard.py")

    print("\n[LOCAL] Deployment complete")
    print("  Dashboard: streamlit run ui/dashboard.py")
    print("  Vast.ai GPU: http://50.217.254.165:40408")


def deploy_docker(mode: str):
    profiles = ["--profile", "gpu"] if mode in ("full", "cloud") else []
    cmd = ["docker-compose", "-f", str(ROOT / "docker-compose.yml")] + profiles + ["up", "-d", "--build"]
    run(cmd, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description="Deploy Legion Omega — MEOK AI Labs")
    parser.add_argument("--mode", choices=["full", "edge", "cloud", "local"], default="local")
    args = parser.parse_args()

    print("🐉 LEGION OMEGA — MEOK AI Labs")
    print(f"Mode: {args.mode}\n")

    check_vast_gpu()
    generate_env()

    if args.mode == "local":
        deploy_local()
    else:
        try:
            run(["docker", "--version"], capture_output=True)
            deploy_docker(args.mode)
        except Exception:
            print("[DOCKER] Docker not available — falling back to local")
            deploy_local()

    print("\n✅ Legion Omega online")


if __name__ == "__main__":
    main()
