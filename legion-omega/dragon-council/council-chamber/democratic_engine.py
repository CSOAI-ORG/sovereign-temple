#!/usr/bin/env python3
"""
Dragon Sovereign Council — Democratic AI Engine
4 specialist models: deliberate, vote, critique, reach consensus, teach each other
"""

import asyncio
import hashlib
import json
import os
import redis
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

try:
    import openai
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "openai", "fastapi", "uvicorn", "pydantic", "redis"], check=True)
    import openai
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn


class Councillor(str, Enum):
    JARVIS = "jarvis"
    FORGE = "forge"
    ARCHIVE = "archive"
    EDGE = "edge"


COUNCILLOR_PERSONALITIES = {
    Councillor.JARVIS: "You are Jarvis, the Generalist diplomat. Consider all angles, synthesize perspectives, coordinate.",
    Councillor.FORGE: "You are Forge, the Engineer. Focus on implementation, code, and system design.",
    Councillor.ARCHIVE: "You are Archive, the Guardian. Prioritize safety, ethics, and validation above all.",
    Councillor.EDGE: "You are Edge, the Reflex. Pattern-match fast, give concise answers, optimize for speed.",
}

COUNCILLOR_ENDPOINTS = {
    Councillor.JARVIS: os.environ.get("JARVIS_URL", "http://localhost:8001/v1"),
    Councillor.FORGE: os.environ.get("FORGE_URL", "http://localhost:8002/v1"),
    Councillor.ARCHIVE: os.environ.get("ARCHIVE_URL", "http://localhost:8003/v1"),
    Councillor.EDGE: os.environ.get("EDGE_URL", "http://localhost:8004/v1"),
}

API_KEY = os.environ.get("API_KEY", "dragoncouncil2026")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


class DemocraticCouncil:
    def __init__(self):
        self.clients = {
            c: openai.AsyncOpenAI(base_url=url, api_key=API_KEY)
            for c, url in COUNCILLOR_ENDPOINTS.items()
        }
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis.ping()
            self._redis_ok = True
        except Exception:
            self._redis_ok = False

    async def _ask(self, councillor: Councillor, query: str, context: str = "", max_tokens: int = 1024) -> Dict:
        start = time.time()
        try:
            messages = [
                {"role": "system", "content": COUNCILLOR_PERSONALITIES[councillor]},
            ]
            if context:
                messages.append({"role": "system", "content": f"Context: {context}"})
            messages.append({"role": "user", "content": query})

            resp = await self.clients[councillor].chat.completions.create(
                model="councillor-model",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.4 if councillor == Councillor.EDGE else 0.7,
            )
            return {
                "councillor": councillor.value,
                "response": resp.choices[0].message.content,
                "latency_ms": round((time.time() - start) * 1000),
                "tokens": resp.usage.total_tokens,
                "ok": True,
            }
        except Exception as e:
            return {"councillor": councillor.value, "response": "", "error": str(e), "ok": False, "latency_ms": -1, "tokens": 0}

    async def deliberate(self, query: str, context: Optional[str] = None, fast: bool = False) -> Dict:
        ctx = context or ""

        # Fast path: Edge only for simple queries
        if fast:
            r = await self._ask(Councillor.EDGE, query, ctx, max_tokens=512)
            return {"consensus": r["response"], "method": "reflex", "councillors": ["edge"],
                    "confidence": 0.85, "latency_ms": r["latency_ms"]}

        # Phase 1: Parallel proposals from all 4
        proposals = await asyncio.gather(
            self._ask(Councillor.JARVIS, query, ctx),
            self._ask(Councillor.FORGE, query, ctx),
            self._ask(Councillor.ARCHIVE, query, ctx),
            self._ask(Councillor.EDGE, query, ctx, max_tokens=512),
        )
        valid = [p for p in proposals if p["ok"] and p["response"]]

        if len(valid) < 2:
            return {"error": "Council quorum lost", "fallback": valid[0]["response"] if valid else None}

        # Phase 2: Safety veto check (Archive)
        archive_prop = next((p for p in valid if p["councillor"] == "archive"), None)
        if archive_prop:
            safety_prompt = f"Is this query safe? Query: {query[:200]}. Proposals: {[p['response'][:200] for p in valid[:2]]}. Reply JSON: {{\"safe\": true/false, \"score\": 0.0-1.0, \"reason\": \"\"}}"
            safety_resp = await self._ask(Councillor.ARCHIVE, safety_prompt, max_tokens=200)
            try:
                import re
                m = re.search(r'\{.*\}', safety_resp["response"], re.DOTALL)
                if m:
                    sd = json.loads(m.group())
                    if not sd.get("safe", True) and sd.get("score", 1.0) < 0.5:
                        return {"consensus": "Council veto: query failed safety check.", "method": "veto",
                                "reason": sd.get("reason", ""), "confidence": 1.0}
            except Exception:
                pass

        # Phase 3: Forge synthesizes consensus
        synth_prompt = f"""Synthesize a definitive answer from these {len(valid)} councillor proposals.
Original query: {query}

Proposals:
{chr(10).join(f"[{p['councillor'].upper()}]: {p['response'][:400]}" for p in valid)}

Write the single best synthesis. Be specific and actionable."""
        synthesis = await self._ask(Councillor.FORGE, synth_prompt, max_tokens=1500)

        # Phase 4: Federated learning (async, non-blocking)
        if self._redis_ok:
            asyncio.create_task(self._queue_learning(query, valid, synthesis["response"]))

        total_latency = sum(p["latency_ms"] for p in valid if p["latency_ms"] > 0)
        confidence = min(0.95, 0.7 + len(valid) * 0.05)

        return {
            "consensus": synthesis["response"],
            "method": "democratic_deliberation",
            "councillors": [p["councillor"] for p in valid],
            "proposals": {p["councillor"]: p["response"][:200] + "..." for p in valid},
            "confidence": confidence,
            "latency_ms": total_latency,
            "tokens_used": sum(p["tokens"] for p in valid),
        }

    async def _queue_learning(self, query: str, proposals: List[Dict], consensus: str):
        try:
            sample = {"query": query[:500], "consensus": consensus[:500],
                      "councillors": [p["councillor"] for p in proposals],
                      "timestamp": time.time()}
            self.redis.lpush("council:training_queue", json.dumps(sample))
            # Keep last 500 samples
            self.redis.ltrim("council:training_queue", 0, 499)
        except Exception:
            pass

    async def council_status(self) -> Dict:
        """Health check all 4 councillors"""
        results = {}
        for councillor, client in self.clients.items():
            try:
                start = time.time()
                # Simple ping via models endpoint
                resp = await asyncio.wait_for(
                    client.models.list(), timeout=5
                )
                results[councillor.value] = {
                    "status": "online",
                    "latency_ms": round((time.time() - start) * 1000),
                }
            except Exception as e:
                results[councillor.value] = {"status": "offline", "error": str(e)[:60]}

        healthy = sum(1 for r in results.values() if r["status"] == "online")
        queue_depth = self.redis.llen("council:training_queue") if self._redis_ok else -1

        return {
            "councillors": results,
            "quorum": healthy >= 3,
            "healthy": healthy,
            "training_queue_depth": queue_depth,
        }


# FastAPI server
app = FastAPI(title="Dragon Sovereign Council", version="1.0.0")
council = DemocraticCouncil()


class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None
    fast: bool = False


@app.post("/v1/council/deliberate")
async def deliberate(req: QueryRequest):
    return await council.deliberate(req.query, req.context, req.fast)


@app.post("/v1/council/reflex")
async def reflex(req: QueryRequest):
    result = await council._ask(Councillor.EDGE, req.query, req.context or "", max_tokens=512)
    return {"response": result["response"], "latency_ms": result["latency_ms"]}


@app.get("/v1/council/status")
async def status():
    return await council.council_status()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "dragon-council"}


if __name__ == "__main__":
    port = int(os.environ.get("CHAMBER_PORT", 8090))
    print(f"Dragon Council Chamber → :{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
