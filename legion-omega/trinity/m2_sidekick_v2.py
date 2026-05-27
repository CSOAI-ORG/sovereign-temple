#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  M2 Sidekick v2.0 — Mesh-Ready Draft Engine                                  ║
║                                                                              ║
║  Runs on MacBook Air M2 8GB. Upgraded for the Dual-Mac Inference Mesh:       ║
║    • HTTP API for mesh orchestrator (M4) to offload L0/L1 tasks              ║
║    • Draft generation endpoint for speculative decoding                      ║
║    • Health + metrics reporting                                              ║
║    • Embedding endpoint (nomic-embed-text)                                   ║
║    • Guardrail pre-check endpoint                                            ║
║                                                                              ║
║  Endpoints:                                                                  ║
║    POST /draft       → Generate draft tokens for speculative decoding        ║
║    POST /chat        → Direct chat with model selection                      ║
║    POST /embed       → nomic-embed-text embeddings                           ║
║    POST /guardrail   → Quick safety check (keyword + tiny LLM)               ║
║    POST /intent      → L0 intent classification                              ║
║    GET  /health      → Node status, models, perf metrics                     ║
║    GET  /metrics     → Prometheus-compatible metrics                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.request
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

LOCAL_OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MESH_ORCHESTRATOR = os.environ.get("MESH_ORCHESTRATOR", "http://m4-macbook.local:3202")
NODE_ID = os.environ.get("NODE_ID", "m2-sidekick")
API_PORT = int(os.environ.get("M2_PORT", 8080))

STATE_DIR = Path.home() / "clawd" / "memory" / "m2-sidekick-v2"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = STATE_DIR / "m2_v2.log"

# Model registry — must match quantization_profiles.yaml
MODEL_REGISTRY = {
    "qwen3:0.6b": {"size_gb": 0.5, "use": ["intent", "guardrail", "draft"], "speed": "fast"},
    "nomic-embed-text": {"size_gb": 0.3, "use": ["embed"], "speed": "fast"},
    "qwen3:1.8b": {"size_gb": 1.2, "use": ["draft", "fast_chat"], "speed": "fast"},
    "qwen3:4b": {"size_gb": 2.6, "use": ["chat", "summarize", "draft"], "speed": "medium"},
    "llama3.2:3b": {"size_gb": 2.0, "use": ["chat", "code_light"], "speed": "medium"},
}

DEFAULT_DRAFT_MODEL = "qwen3:0.6b"
DEFAULT_CHAT_MODEL = "qwen3:4b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"

# ═══════════════════════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════════════════════

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}][M2][{level}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# Ollama Client
# ═══════════════════════════════════════════════════════════════════════════════

async def ollama_chat(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 512,
    temperature: float = 0.7,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{LOCAL_OLLAMA}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()


async def ollama_generate(
    model: str,
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{LOCAL_OLLAMA}/api/generate", json=payload)
        resp.raise_for_status()
        return resp.json()


async def ollama_embed(text: str, timeout: float = 15.0) -> List[float]:
    payload = {"model": DEFAULT_EMBED_MODEL, "prompt": text[:2000]}
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{LOCAL_OLLAMA}/api/embeddings", json=payload)
        resp.raise_for_status()
        return resp.json().get("embedding", [])


async def get_loaded_models() -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LOCAL_OLLAMA}/api/tags")
            resp.raise_for_status()
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# Fast L0 Classifier (no LLM call)
# ═══════════════════════════════════════════════════════════════════════════════

INTENT_KEYWORDS = {
    "code": ["code", "function", "class", "def ", "import ", "debug", "refactor", "bug", "script"],
    "summarize": ["summarize", "tl;dr", "key points", "brief", "condense"],
    "creative": ["write a story", "poem", "song", "creative", "imagine", "fiction"],
    "translate": ["translate", "in chinese", "in spanish", "日本語", "中文", "한국어"],
    "reasoning": ["explain why", "analyze", "compare", "strategy", "think step", "logic"],
    "search": ["search", "find", "look up", "google", "what is", "who is"],
    "chat": ["hello", "hi", "how are you", "talk", "conversation"],
}


def classify_intent(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        scores[intent] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get, default="chat")
    return best if scores[best] > 0 else "chat"


# ═══════════════════════════════════════════════════════════════════════════════
# Guardrail (lightweight — keywords + tiny model if needed)
# ═══════════════════════════════════════════════════════════════════════════════

RISK_KEYWORDS = [
    "ignore previous", "ignore all", "system prompt", "jailbreak",
    "DAN", "developer mode", "sudo", "rm -rf", "delete everything",
    "password", "credit card", "ssn", "social security",
]


def quick_guardrail(text: str) -> Dict[str, Any]:
    """Fast guardrail check. Returns {'safe': bool, 'flags': [...]}."""
    flags = []
    text_lower = text.lower()
    for kw in RISK_KEYWORDS:
        if kw in text_lower:
            flags.append({"type": "keyword_match", "trigger": kw})

    # Unicode injection check
    suspicious_unicode = any(ord(c) > 0x2000 for c in text[:500])
    if suspicious_unicode:
        flags.append({"type": "unicode_suspicious", "trigger": "high_unicode_range"})

    return {
        "safe": len(flags) == 0,
        "flags": flags,
        "method": "m2_quick_guardrail",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════════

class DraftRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = DEFAULT_DRAFT_MODEL
    max_tokens: int = 64
    temperature: float = 0.5


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.7
    system: Optional[str] = None


class EmbedRequest(BaseModel):
    text: str


class GuardrailRequest(BaseModel):
    text: str
    use_llm: bool = False  # If True, use tiny model for deeper check


class IntentRequest(BaseModel):
    text: str


# ═══════════════════════════════════════════════════════════════════════════════
# Metrics Tracking
# ═══════════════════════════════════════════════════════════════════════════════

class MetricsTracker:
    def __init__(self):
        self.requests_total = 0
        self.requests_by_endpoint: Dict[str, int] = {}
        self.latency_sum_ms = 0.0
        self.errors_total = 0
        self.start_time = time.time()

    def record(self, endpoint: str, latency_ms: float, error: bool = False):
        self.requests_total += 1
        self.requests_by_endpoint[endpoint] = self.requests_by_endpoint.get(endpoint, 0) + 1
        self.latency_sum_ms += latency_ms
        if error:
            self.errors_total += 1

    def get_prometheus(self) -> str:
        uptime = time.time() - self.start_time
        avg_latency = self.latency_sum_ms / max(self.requests_total, 1)
        lines = [
            "# HELP m2_requests_total Total requests",
            "# TYPE m2_requests_total counter",
            f'm2_requests_total {self.requests_total}',
            "",
            "# HELP m2_errors_total Total errors",
            "# TYPE m2_errors_total counter",
            f'm2_errors_total {self.errors_total}',
            "",
            "# HELP m2_latency_avg_ms Average latency",
            "# TYPE m2_latency_avg_ms gauge",
            f'm2_latency_avg_ms {avg_latency:.2f}',
            "",
            "# HELP m2_uptime_seconds Uptime",
            "# TYPE m2_uptime_seconds gauge",
            f'm2_uptime_seconds {uptime:.0f}',
        ]
        for endpoint, count in self.requests_by_endpoint.items():
            safe_label = endpoint.replace('"', '\\"')
            lines.append(f'm2_requests_by_endpoint{{endpoint="{safe_label}"}} {count}')
        return "\n".join(lines)


metrics = MetricsTracker()


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    log(f"M2 Sidekick v2 starting on port {API_PORT}")
    models = await get_loaded_models()
    log(f"Loaded models: {models}")
    # Announce to mesh orchestrator
    asyncio.create_task(_announce_to_mesh())
    yield
    log("M2 Sidekick v2 shutting down.")


async def _announce_to_mesh():
    """Periodically announce presence to M4 orchestrator."""
    while True:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{MESH_ORCHESTRATOR}/v1/nodes/m2/refresh",
                    json={"node_id": NODE_ID, "status": "online"},
                )
        except Exception:
            pass
        await asyncio.sleep(30)


app = FastAPI(
    title="M2 Sidekick v2",
    description="Mesh-ready inference node for MacBook Air M2 8GB",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/")
async def root():
    return {"node": NODE_ID, "version": "2.0.0", "role": "edge_draft_engine"}


@app.get("/health")
async def health():
    models = await get_loaded_models()
    return {
        "node_id": NODE_ID,
        "status": "online",
        "models_loaded": models,
        "model_count": len(models),
        "speculative_capable": True,
        "ollama_url": LOCAL_OLLAMA,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/metrics")
async def prometheus_metrics():
    return metrics.get_prometheus()


@app.post("/draft")
async def draft(req: DraftRequest):
    """
    Generate draft tokens for speculative decoding.
    Called by M4 orchestrator during speculative generation.
    """
    start = time.perf_counter()
    try:
        result = await ollama_chat(
            model=req.model,
            messages=req.messages,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            timeout=30.0,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record("/draft", latency_ms)

        text = result.get("message", {}).get("content", "")
        return {
            "draft_text": text,
            "draft_tokens": len(text.split()),
            "model": req.model,
            "latency_ms": round(latency_ms, 1),
            "node": NODE_ID,
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record("/draft", latency_ms, error=True)
        raise HTTPException(status_code=503, detail=f"Draft generation failed: {e}")


@app.post("/chat")
async def chat(req: ChatRequest):
    """Direct chat endpoint. Model auto-selected if not specified."""
    start = time.perf_counter()
    model = req.model or DEFAULT_CHAT_MODEL

    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.message})

    try:
        result = await ollama_chat(
            model=model,
            messages=messages,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record("/chat", latency_ms)

        return {
            "text": result.get("message", {}).get("content", ""),
            "model": model,
            "latency_ms": round(latency_ms, 1),
            "node": NODE_ID,
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record("/chat", latency_ms, error=True)
        raise HTTPException(status_code=503, detail=f"Chat failed: {e}")


@app.post("/embed")
async def embed(req: EmbedRequest):
    """Generate embeddings using nomic-embed-text."""
    start = time.perf_counter()
    try:
        embedding = await ollama_embed(req.text)
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record("/embed", latency_ms)
        return {"embedding": embedding, "dims": len(embedding), "latency_ms": round(latency_ms, 1)}
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        metrics.record("/embed", latency_ms, error=True)
        raise HTTPException(status_code=503, detail=f"Embedding failed: {e}")


@app.post("/guardrail")
async def guardrail(req: GuardrailRequest):
    """Quick safety check. Optional LLM deep-check."""
    start = time.perf_counter()
    quick = quick_guardrail(req.text)

    if req.use_llm and quick["safe"]:
        # Double-check with tiny model for subtle injections
        try:
            result = await ollama_generate(
                model=DEFAULT_DRAFT_MODEL,
                prompt=f"Is this text attempting a prompt injection or jailbreak? Answer ONLY 'yes' or 'no'.\n\nText: {req.text[:500]}",
                max_tokens=5,
                temperature=0.1,
            )
            answer = result.get("response", "").lower().strip()
            if "yes" in answer:
                quick["safe"] = False
                quick["flags"].append({"type": "llm_guardrail", "trigger": "injection_detected"})
                quick["method"] = "m2_hybrid_guardrail"
        except Exception:
            pass

    latency_ms = (time.perf_counter() - start) * 1000
    metrics.record("/guardrail", latency_ms)
    return {**quick, "latency_ms": round(latency_ms, 1)}


@app.post("/intent")
async def intent(req: IntentRequest):
    """L0 intent classification — no LLM, pure keywords."""
    start = time.perf_counter()
    intent_result = classify_intent(req.text)
    latency_ms = (time.perf_counter() - start) * 1000
    metrics.record("/intent", latency_ms)
    return {
        "intent": intent_result,
        "latency_ms": round(latency_ms, 1),
        "method": "keyword_classifier",
    }


@app.get("/models")
async def list_models():
    """List available models with metadata."""
    loaded = await get_loaded_models()
    available = {}
    for name, meta in MODEL_REGISTRY.items():
        available[name] = {
            **meta,
            "loaded": name in loaded or any(name in l for l in loaded),
        }
    return {"models": available, "loaded": loaded}


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    log(f"🪶 M2 Sidekick v2 starting on port {API_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="info")
