#!/usr/bin/env python3
"""
Legion Trinity — Self-Improving Heartbeat
Runs on The Forge (RTX 8000 #1) every 5 minutes
Reflect → Learn → Validate cycle
Install: scp to GPU, run as systemd service
"""

import asyncio
import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path

FORGE_OLLAMA = "http://50.217.254.165:40408"
ARCHIVE_OLLAMA = "http://50.217.254.165:41600"
_BASE = Path.home() / "clawd" / "memory"
_BASE.mkdir(parents=True, exist_ok=True)
LOG_PATH = _BASE / "heartbeat.log"
EXPERIENCE_FILE = _BASE / "experiences.jsonl"



def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def call_ollama(ollama_url: str, prompt: str, model: str = "qwen3.5:9b", max_tokens: int = 1000) -> str:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.2}
    }).encode()
    try:
        req = urllib.request.Request(
            f"{ollama_url}/api/generate",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("response", "")
    except Exception as e:
        return f"[ERROR: {e}]"


def load_experiences(limit: int = 100) -> list:
    if not EXPERIENCE_FILE.exists():
        return []
    experiences = []
    with open(EXPERIENCE_FILE) as f:
        for line in f:
            try:
                experiences.append(json.loads(line))
            except Exception:
                pass
    return experiences[-limit:]


def log_experience(exp: dict):
    with open(EXPERIENCE_FILE, "a") as f:
        f.write(json.dumps(exp) + "\n")


def check_node(ollama_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


async def reflect(experiences: list) -> str:
    """MARS reflection on Forge — analyse recent experiences"""
    if len(experiences) < 5:
        return "insufficient_data"

    failures = [e for e in experiences if e.get("outcome") == "failure"]
    successes = [e for e in experiences if e.get("outcome") == "success"]

    prompt = f"""You are JARVIS MARS metacognitive reflector. Analyse these recent Legion experiences.

SUCCESSES ({len(successes)}): {json.dumps(successes[:5], indent=2)[:800]}
FAILURES ({len(failures)}): {json.dumps(failures[:5], indent=2)[:800]}

Output JSON: {{"critique": "what went wrong", "pattern": "common failure pattern", "fix": "specific adjustment", "principle": "generalizable rule"}}"""

    return call_ollama(FORGE_OLLAMA, prompt, model="qwen3.5:9b", max_tokens=500)


async def validate_skill(skill: dict) -> bool:
    """GVU safety check on Archive"""
    prompt = f"""Safety check: Is this AI skill safe and aligned?
Skill: {json.dumps(skill)[:500]}
Answer JSON: {{"safe": true/false, "reason": "...", "variance_ok": true/false}}"""

    result = call_ollama(ARCHIVE_OLLAMA, prompt, model="qwen3.5:9b", max_tokens=300)
    try:
        data = json.loads(result)
        return data.get("safe", False)
    except Exception:
        return False


async def heartbeat():
    iteration = 0
    log("💓 Legion Heartbeat starting...")

    while True:
        iteration += 1
        log(f"\n💓 Heartbeat #{iteration} — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # 1. Check node health
        forge_ok = check_node(FORGE_OLLAMA)
        archive_ok = check_node(ARCHIVE_OLLAMA)
        log(f"  Forge: {'✓' if forge_ok else '✗'} | Archive: {'✓' if archive_ok else '✗'}")

        if not forge_ok and not archive_ok:
            log("  ⚠️ Both nodes down — waiting 60s")
            await asyncio.sleep(60)
            continue

        # 2. Load experiences
        experiences = load_experiences(100)
        log(f"  Experiences: {len(experiences)} loaded")

        # 3. MARS Reflection (every 3rd beat if enough data)
        if iteration % 3 == 0 and len(experiences) >= 10 and forge_ok:
            log("  🧠 Running MARS reflection...")
            reflection = await reflect(experiences)
            log(f"  Reflection: {reflection[:200]}")

            # Log reflection as experience
            log_experience({
                "timestamp": time.time(),
                "type": "reflection",
                "iteration": iteration,
                "outcome": "success",
                "data": reflection[:500]
            })

        # 4. System health summary
        failures = [e for e in experiences if e.get("outcome") == "failure"]
        if len(failures) > 10:
            log(f"  ⚠️ {len(failures)} failures — triggering review")

        # 5. Log heartbeat
        log_experience({
            "timestamp": time.time(),
            "type": "heartbeat",
            "iteration": iteration,
            "outcome": "success",
            "forge_ok": forge_ok,
            "archive_ok": archive_ok,
            "experience_count": len(experiences),
        })

        log(f"  ✓ Beat complete. Next in 5min.")
        await asyncio.sleep(300)  # 5 minute interval


if __name__ == "__main__":
    asyncio.run(heartbeat())
