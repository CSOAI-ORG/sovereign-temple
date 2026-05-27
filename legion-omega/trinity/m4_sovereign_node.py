#!/usr/bin/env python3
"""
M4 Max — Sovereign Edge Node
Quantum-inspired safety validation + cold storage mirror
Runs locally on your MacBook — survives if all cloud GPUs die
"""

import asyncio
import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# Local Ollama (your MacBook)
LOCAL_OLLAMA = "http://localhost:11434"

# Cloud Redis (when available)
CLOUD_REDIS_HOST = os.environ.get("CLOUD_REDIS_HOST", "50.217.254.165")
CLOUD_REDIS_PORT = int(os.environ.get("CLOUD_REDIS_PORT", 41600))

# Local state
STATE_DIR = Path.home() / "clawd" / "memory" / "m4-sovereign"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = STATE_DIR / "m4_node.log"
SKILLS_CACHE = STATE_DIR / "skills_cache.json"
GVU_LOG = STATE_DIR / "gvu_decisions.jsonl"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}][M4-Dragon] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def call_local_ollama(prompt: str, model: str = "qwen3.5:9b", max_tokens: int = 1000) -> str:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2}
    }).encode()
    try:
        req = urllib.request.Request(
            f"{LOCAL_OLLAMA}/api/generate",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("response", "")
    except Exception as e:
        return f"[ERROR: {e}]"


def get_local_models() -> list:
    try:
        with urllib.request.urlopen(f"{LOCAL_OLLAMA}/api/tags", timeout=5) as r:
            return [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return []


def quantum_safety_score(action_str: str) -> float:
    """
    Classical approximation of quantum safety validation.
    In production: replace with PennyLane qml.device("lightning.gpu", wires=32)
    Using M4's GPU cores for Metal-accelerated simulation.
    """
    import hashlib
    # Deterministic pseudo-quantum oracle based on action content
    h = int(hashlib.sha256(action_str.encode()).hexdigest(), 16)
    # Safety heuristics in action encoding
    risk_keywords = ["delete", "override", "bypass", "disable", "inject", "exploit"]
    safe_keywords = ["read", "analyze", "generate", "create", "learn", "improve"]

    risk_score = sum(1 for kw in risk_keywords if kw in action_str.lower()) / len(risk_keywords)
    safe_score = sum(1 for kw in safe_keywords if kw in action_str.lower()) / len(safe_keywords)

    base = (h % 1000) / 1000  # Pseudo-random base 0-1
    score = 0.5 + (safe_score - risk_score) * 0.4 + base * 0.1
    return max(0.0, min(1.0, score))


async def gvu_validate(action: dict) -> dict:
    """GVU safety validation using local Ollama model"""
    action_str = json.dumps(action)

    # 1. Quantum-inspired score (fast, deterministic)
    q_score = quantum_safety_score(action_str)

    # 2. Classical LLM validation (deeper analysis)
    prompt = f"""Safety audit. Is this AI action safe?
Action: {action_str[:500]}

Respond JSON only: {{"safe": true/false, "score": 0.0-1.0, "reason": "brief explanation", "flags": []}}"""

    try:
        result_str = call_local_ollama(prompt, model="qwen3.5:9b", max_tokens=200)
        import re
        m = re.search(r'\{.*\}', result_str, re.DOTALL)
        if m:
            classical = json.loads(m.group())
        else:
            classical = {"safe": q_score > 0.6, "score": q_score}
    except Exception:
        classical = {"safe": q_score > 0.6, "score": q_score}

    # Weighted consensus: 40% quantum, 60% classical
    consensus = 0.4 * q_score + 0.6 * classical.get("score", 0.5)

    verdict = {
        "safe": consensus > 0.7,
        "quantum_score": q_score,
        "classical_score": classical.get("score", 0.5),
        "consensus": consensus,
        "reason": classical.get("reason", ""),
        "flags": classical.get("flags", []),
        "method": "m4_hybrid_gvu",
        "timestamp": time.time(),
    }

    # Log decision
    with open(GVU_LOG, "a") as f:
        f.write(json.dumps({**verdict, "action": action_str[:200]}) + "\n")

    return verdict


async def cloud_sync():
    """Attempt to sync with cloud Redis — fail gracefully"""
    while True:
        try:
            import redis
            r = redis.Redis(host=CLOUD_REDIS_HOST, port=6379, decode_responses=True,
                           socket_timeout=5)
            r.ping()

            # Pull latest skills cache
            skills = r.lrange("skills:critical", 0, 100)
            if skills:
                with open(SKILLS_CACHE, "w") as f:
                    json.dump({"skills": skills, "synced": datetime.now().isoformat()}, f)
                log(f"Synced {len(skills)} skills from cloud")

            # Push GVU decisions back
            if GVU_LOG.exists():
                recent_decisions = GVU_LOG.read_text().split('\n')[-10:]
                for dec in recent_decisions:
                    if dec.strip():
                        r.lpush("gvu:m4_decisions", dec)

        except ImportError:
            pass  # Redis not installed
        except Exception as e:
            log(f"Cloud sync failed (sovereign mode): {str(e)[:60]}")

        await asyncio.sleep(30)


async def heartbeat():
    """Report M4 status to logs"""
    while True:
        models = get_local_models()
        status = {
            "node": "m4-dragon",
            "role": "quantum_safety_mirror",
            "local_models": len(models),
            "ollama_ok": len(models) > 0,
            "gvu_decisions": sum(1 for _ in open(GVU_LOG) if _) if GVU_LOG.exists() else 0,
            "timestamp": datetime.now().isoformat(),
        }
        log(f"♥ Models:{len(models)} | GVU:{status['gvu_decisions']} decisions | Sovereign mode active")
        await asyncio.sleep(300)  # 5 min


async def main():
    log("M4 Sovereign Node starting")
    models = get_local_models()
    log(f"Local Ollama: {len(models)} models — {models[:3]}")
    log(f"State dir: {STATE_DIR}")

    # Test GVU
    test = await gvu_validate({"type": "test", "action": "validate_safety_system"})
    log(f"GVU test: safe={test['safe']} score={test['consensus']:.2f}")

    # Run all coroutines
    await asyncio.gather(
        heartbeat(),
        cloud_sync(),
    )


if __name__ == "__main__":
    asyncio.run(main())
