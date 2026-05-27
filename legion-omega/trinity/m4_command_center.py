#!/usr/bin/env python3
"""
M4 Air — Solo Fire Command Center
Smart router: 4080S (fast/cheap) → RTX 8000s (heavy/auto-scale)
Saves ~$450/month vs running heavy lifters 24/7
Usage: python m4_command_center.py
"""

import asyncio
import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# GPU Endpoints
SPEED_4080S = os.environ.get("SPEED_4080S_URL", "http://120.238.149.205")  # RTX 5090 port TBD
FORGE_URL = "http://50.217.254.165:40408"
ARCHIVE_URL = "http://50.217.254.165:41600"
DRAGON_COUNCIL_URL = "http://50.217.254.173:41021"

# Auto-scale config
HEAVY_IDLE_TIMEOUT = int(os.environ.get("HEAVY_IDLE_TIMEOUT", 600))  # 10 min
HEAVY_INSTANCES = ["34060491", "34076369", "34077918"]  # Vast.ai instance IDs

STATE_DIR = Path.home() / "clawd" / "memory" / "command-center"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = STATE_DIR / "command_center.log"
COST_LOG = STATE_DIR / "cost_tracker.jsonl"


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}][CMD] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def call_ollama(url: str, prompt: str, model: str = "qwen3.5:9b", max_tokens: int = 2000) -> str:
    payload = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.3}
    }).encode()
    try:
        req = urllib.request.Request(
            f"{url}/api/generate",
            data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()).get("response", "")
    except Exception as e:
        return f"[ERROR: {e}]"


def check_node(ollama_url: str, timeout: int = 5) -> bool:
    try:
        with urllib.request.urlopen(f"{ollama_url}/api/tags", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def analyze_task(query: str) -> dict:
    """Classify query without GPU — pure Python logic"""
    q = query.lower()
    tokens_est = len(query.split()) * 1.5

    is_heavy = any(k in q for k in [
        "analyze document", "100 page", "405b", "long context",
        "full codebase", "fine-tune", "train", "batch process"
    ])
    is_code = any(k in q for k in ["code", "function", "script", "debug", "implement"])
    is_urgent = "urgent" in q or "now" in q or "asap" in q

    if is_heavy or tokens_est > 8000:
        tier = "heavy"
    elif is_code:
        tier = "forge"
    elif tokens_est < 1000 and not is_code:
        tier = "speed"
    else:
        tier = "standard"

    return {
        "tier": tier, "tokens_est": int(tokens_est),
        "urgent": is_urgent, "code": is_code
    }


class CommandCenter:
    def __init__(self):
        self.heavy_online = True  # Assume running at startup
        self.last_heavy_job = time.time()
        self._cost_session_start = time.time()
        self._heavy_hours = 0.0

    async def route(self, query: str, context: str = "") -> dict:
        profile = analyze_task(query)
        tier = profile["tier"]

        # Try routing
        if tier == "speed":
            result = await self._call_speed(query)
        elif tier == "forge":
            result = await self._call_node(FORGE_URL, query, model="qwen3.5:35b")
        elif tier == "heavy":
            if not self.heavy_online:
                log("Heavy needed but offline — starting up (3 min)")
                await self._start_heavy()
            result = await self._call_node(FORGE_URL, query, model="qwen3.5:35b")
            self.last_heavy_job = time.time()
        else:
            result = await self._call_node(ARCHIVE_URL, query)

        self._log_cost(tier)
        return {**result, "tier": tier, "profile": profile}

    async def _call_speed(self, query: str) -> dict:
        """Route to fastest available node"""
        nodes = [
            (DRAGON_COUNCIL_URL, "dragon-council"),
            (ARCHIVE_URL, "archive"),
            (FORGE_URL, "forge"),
        ]
        for url, name in nodes:
            if check_node(url, timeout=3):
                resp = await asyncio.get_event_loop().run_in_executor(
                    None, lambda u=url: call_ollama(u, query, model="qwen3.5:9b", max_tokens=1000)
                )
                return {"response": resp, "node": name, "model": "qwen3.5:9b"}
        return {"response": "All nodes offline", "node": "none", "error": True}

    async def _call_node(self, url: str, query: str, model: str = "qwen3.5:9b") -> dict:
        """Call a specific Ollama node"""
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: call_ollama(url, query, model=model)
        )
        return {"response": resp, "node": url.split(":")[1].lstrip("/"), "model": model}

    async def _start_heavy(self):
        """Wake heavy lifters via Vast.ai CLI"""
        for inst_id in HEAVY_INSTANCES:
            subprocess.run(["vastai", "start", "instance", inst_id], capture_output=True)
        log(f"Starting {len(HEAVY_INSTANCES)} heavy instances...")
        await asyncio.sleep(180)  # 3 min startup
        self.heavy_online = True
        log("Heavy lifters online")

    async def _stop_heavy(self):
        """Shutdown heavy lifters to save money"""
        log(f"Idle {HEAVY_IDLE_TIMEOUT}s — stopping heavy lifters to save cost")
        for inst_id in HEAVY_INSTANCES:
            subprocess.run(["vastai", "stop", "instance", inst_id], capture_output=True)
        self.heavy_online = False
        self._heavy_hours += (time.time() - self.last_heavy_job) / 3600

    def _log_cost(self, tier: str):
        cost_per_query = {"speed": 0.0001, "forge": 0.001, "heavy": 0.01, "standard": 0.002}
        entry = {
            "timestamp": time.time(), "tier": tier,
            "cost_est": cost_per_query.get(tier, 0.001)
        }
        with open(COST_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")

    async def auto_scale_monitor(self):
        """Background: shutdown heavy after idle timeout"""
        while True:
            await asyncio.sleep(60)
            if self.heavy_online:
                idle = time.time() - self.last_heavy_job
                if idle > HEAVY_IDLE_TIMEOUT:
                    await self._stop_heavy()

    def status(self) -> dict:
        # Calculate costs
        session_hrs = (time.time() - self._cost_session_start) / 3600
        heavy_cost = self._heavy_hours * (0.219 * 3)  # 3 RTX 8000s
        dragon_council_cost = session_hrs * 0.259

        return {
            "nodes": {
                "forge": check_node(FORGE_URL),
                "archive": check_node(ARCHIVE_URL),
                "dragon-council": check_node(DRAGON_COUNCIL_URL),
            },
            "heavy_online": self.heavy_online,
            "session_hours": round(session_hrs, 2),
            "estimated_cost_usd": round(heavy_cost + dragon_council_cost, 3),
            "monthly_projection": round((heavy_cost + dragon_council_cost) / max(session_hrs, 0.01) * 730, 2),
        }


# FastAPI server
try:
    from fastapi import FastAPI
    from pydantic import BaseModel
    import uvicorn

    app = FastAPI(title="M4 Command Center", version="1.0.0")
    center = CommandCenter()

    class QueryRequest(BaseModel):
        query: str
        context: str = ""

    @app.post("/query")
    async def query_endpoint(req: QueryRequest):
        return await center.route(req.query, req.context)

    @app.get("/status")
    async def status():
        return center.status()

    @app.get("/health")
    async def health():
        return {"status": "ok", "node": "m4-command-center"}

    if __name__ == "__main__":
        asyncio.get_event_loop().create_task(center.auto_scale_monitor())
        log("M4 Command Center starting on :8090")
        uvicorn.run(app, host="0.0.0.0", port=8090)

except ImportError:
    if __name__ == "__main__":
        log("FastAPI not installed. Run: pip install fastapi uvicorn")
