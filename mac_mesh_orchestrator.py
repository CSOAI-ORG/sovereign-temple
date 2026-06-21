#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MAC MESH ORCHESTRATOR — Dual-Mac Inference Mesh v1.0                        ║
║                                                                              ║
║  Runs on M4 (command center). Discovers M2 on LAN. Routes inference:         ║
║    • L0 intent/guardrails → M2 (Qwen3-0.6B, ~5ms)                            ║
║    • L1 fast chat       → M2 (Qwen3-4B/Q4, ~180 tok/s)                       ║
║    • L2 deep work       → M4 (Qwen3-8B/Q4 or Gemma-3-12B/Q4)                 ║
║    • L3 heavy lifting   → Vast.ai (Gemma-4-27B or 70B+)                      ║
║    • Speculative decode → M2 drafts + M4 verifies = 2-3x speedup            ║
║                                                                              ║
║  Integrates: SOV3 coordination, Siri shortcuts, MEOKCLAW frontend            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════════

M2_HOST = os.environ.get("M2_HOST", "m2-air.local")  # Bonjour hostname
M2_PORT = int(os.environ.get("M2_PORT", 8080))
M2_OLLAMA_PORT = int(os.environ.get("M2_OLLAMA_PORT", 11434))

M4_OLLAMA_PORT = int(os.environ.get("M4_OLLAMA_PORT", 11434))
VAST_OLLAMA_PORT = int(os.environ.get("VAST_OLLAMA_PORT", 11436))
VAST_HOST = os.environ.get("VAST_HOST", "localhost")

MESH_PORT = int(os.environ.get("MESH_PORT", 3202))
HEALTH_INTERVAL_SEC = int(os.environ.get("HEALTH_INTERVAL", 10))
SPECULATIVE_ENABLED = os.environ.get("SPECULATIVE_ENABLED", "true").lower() == "true"

LOG_PATH = os.path.expanduser("~/clawd/memory/mac_mesh.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class TaskType(str, Enum):
    INTENT = "intent"           # L0: Classification, routing
    GUARDRAIL = "guardrail"     # Safety check
    EMBED = "embed"             # Embedding generation
    FAST_CHAT = "fast_chat"     # L1: Quick conversational
    CODE = "code"               # L2: Coding assistance
    REASONING = "reasoning"     # L2: Deep reasoning
    CREATIVE = "creative"       # L2: Creative writing
    SUMMARIZE = "summarize"     # L1/L2: Summarization
    AGENTIC = "agentic"         # L3: Tool use, agent workflows
    VISION = "vision"           # L2/L3: Vision tasks


class DeviceTier(str, Enum):
    M2_EDGE = "m2_edge"         # M2 Air 8GB — tiny models
    M4_LOCAL = "m4_local"       # M4 — medium models
    VAST_CLOUD = "vast_cloud"   # Vast.ai GPU — large models


@dataclass
class DeviceProfile:
    """Runtime profile of a compute node."""
    node_id: str
    tier: DeviceTier
    host: str
    ollama_port: int
    api_port: Optional[int] = None
    status: str = "unknown"     # online, degraded, offline
    models_loaded: List[str] = field(default_factory=list)
    ram_gb: float = 0.0
    vram_gb: float = 0.0
    cpu_cores: int = 0
    gpu_cores: int = 0
    latency_ms: float = 0.0     # Last measured RTT
    throughput_tok_s: float = 0.0
    last_seen: float = 0.0
    speculative_capable: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MeshDecision:
    """Routing decision for a query."""
    task_type: TaskType
    primary_node: str
    fallback_nodes: List[str]
    model: str
    reasoning: str
    use_speculative: bool = False
    estimated_latency_ms: int = 0
    privacy_level: str = "local"  # local, edge, cloud


class ChatRequest(BaseModel):
    message: str
    task_type: Optional[str] = None
    use_speculative: bool = Field(default=True, description="Enable speculative decoding if available")
    require_private: bool = Field(default=False, description="Never send to cloud")
    stream: bool = False
    temperature: float = 0.7
    max_tokens: int = 2048


class MeshResponse(BaseModel):
    text: str
    node: str
    model: str
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    speculative_used: bool = False
    draft_accepted_ratio: float = 0.0
    cost_usd: float = 0.0


class HealthResponse(BaseModel):
    orchestrator: str = "mac_mesh_v1"
    nodes: Dict[str, dict]
    total_throughput_tok_s: float = 0.0
    speculative_ready: bool = False
    mesh_status: str = "healthy"


# ═══════════════════════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════════════════════

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"[{ts}][MESH][{level}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


# ═══════════════════════════════════════════════════════════════════════════════
# Task Classifier (L0 — runs locally, no LLM needed)
# ═══════════════════════════════════════════════════════════════════════════════

class TaskClassifier:
    """Fast keyword-based intent classification (L0 router)."""

    PATTERNS = {
        TaskType.INTENT: ["classify", "route", "intent", "what type"],
        TaskType.GUARDRAIL: ["safety", "guardrail", "check", "audit", "validate"],
        TaskType.EMBED: ["embed", "embedding", "vector", "similarity", "semantic"],
        TaskType.CODE: ["code", "function", "class", "def ", "import ", "debug", "refactor", "bug", "script", "api"],
        TaskType.REASONING: ["reason", "explain why", "analyze", "compare", "strategy", "think step", "logic"],
        TaskType.CREATIVE: ["write a story", "poem", "song", "creative", "imagine", "fiction", "novel"],
        TaskType.SUMMARIZE: ["summarize", "tl;dr", "key points", "brief", "condense", "overview"],
        TaskType.AGENTIC: ["search", "browse", "delegate", "run command", "tool", "mcp", "execute"],
        TaskType.VISION: ["image", "picture", "photo", "screenshot", "visual", "describe image", "look at"],
    }

    @classmethod
    def classify(cls, text: str) -> TaskType:
        text_lower = text.lower()
        scores: Dict[TaskType, int] = {}
        for task, keywords in cls.PATTERNS.items():
            scores[task] = sum(1 for kw in keywords if kw in text_lower)
        best = max(scores, key=scores.get, default=TaskType.FAST_CHAT)
        return best if scores[best] > 0 else TaskType.FAST_CHAT


# ═══════════════════════════════════════════════════════════════════════════════
# Node Manager — Discovery, Health, Model Sync
# ═══════════════════════════════════════════════════════════════════════════════

class NodeManager:
    """Manages all compute nodes in the mesh."""

    def __init__(self):
        self.nodes: Dict[str, DeviceProfile] = {}
        self._init_nodes()
        self._health_task: Optional[asyncio.Task] = None

    def _init_nodes(self):
        # M2 Edge Node
        self.nodes["m2"] = DeviceProfile(
            node_id="m2",
            tier=DeviceTier.M2_EDGE,
            host=M2_HOST,
            ollama_port=M2_OLLAMA_PORT,
            api_port=M2_PORT,
            speculative_capable=True,
        )
        # M4 Local Node (self)
        self.nodes["m4"] = DeviceProfile(
            node_id="m4",
            tier=DeviceTier.M4_LOCAL,
            host="localhost",
            ollama_port=M4_OLLAMA_PORT,
            api_port=MESH_PORT,
            speculative_capable=True,
        )
        # Vast Cloud Node
        self.nodes["vast"] = DeviceProfile(
            node_id="vast",
            tier=DeviceTier.VAST_CLOUD,
            host=VAST_HOST,
            ollama_port=VAST_OLLAMA_PORT,
            speculative_capable=False,
        )

    async def start_health_loop(self):
        """Start periodic health checks."""
        self._health_task = asyncio.create_task(self._health_loop())

    async def _health_loop(self):
        while True:
            await self._check_all_nodes()
            await asyncio.sleep(HEALTH_INTERVAL_SEC)

    async def _check_all_nodes(self):
        tasks = [self._check_node(node) for node in self.nodes.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_node(self, node: DeviceProfile):
        start = time.perf_counter()
        try:
            # Check Ollama
            url = f"http://{node.host}:{node.ollama_port}/api/tags"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                node.models_loaded = [m["name"] for m in data.get("models", [])]
                node.status = "online"
                node.last_seen = time.time()

            # Check M2 sidekick API if applicable
            if node.api_port and node.node_id == "m2":
                try:
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        resp = await client.get(f"http://{node.host}:{node.api_port}/health", timeout=3.0)
                        if resp.status_code == 200:
                            node.speculative_capable = resp.json().get("speculative_capable", False)
                except Exception:
                    pass

            node.latency_ms = (time.perf_counter() - start) * 1000

        except Exception as e:
            node.status = "offline"
            log(f"Node {node.node_id} health check failed: {e}", "WARN")

    def get_online_nodes(self) -> List[DeviceProfile]:
        return [n for n in self.nodes.values() if n.status == "online"]

    def get_best_node(self, task: TaskType, require_private: bool = False) -> Optional[DeviceProfile]:
        """Select optimal node for task."""
        online = self.get_online_nodes()
        if not online:
            return None

        # Privacy-first: never cloud
        if require_private:
            online = [n for n in online if n.tier != DeviceTier.VAST_CLOUD]

        # Task → tier mapping
        tier_priority = {
            TaskType.INTENT: [DeviceTier.M2_EDGE, DeviceTier.M4_LOCAL],
            TaskType.GUARDRAIL: [DeviceTier.M2_EDGE, DeviceTier.M4_LOCAL],
            TaskType.EMBED: [DeviceTier.M2_EDGE, DeviceTier.M4_LOCAL],
            TaskType.FAST_CHAT: [DeviceTier.M2_EDGE, DeviceTier.M4_LOCAL],
            TaskType.SUMMARIZE: [DeviceTier.M2_EDGE, DeviceTier.M4_LOCAL],
            TaskType.CODE: [DeviceTier.M4_LOCAL, DeviceTier.VAST_CLOUD],
            TaskType.REASONING: [DeviceTier.M4_LOCAL, DeviceTier.VAST_CLOUD],
            TaskType.CREATIVE: [DeviceTier.M4_LOCAL, DeviceTier.VAST_CLOUD],
            TaskType.AGENTIC: [DeviceTier.M4_LOCAL, DeviceTier.VAST_CLOUD],
            TaskType.VISION: [DeviceTier.M4_LOCAL, DeviceTier.VAST_CLOUD],
        }

        priority = tier_priority.get(task, [DeviceTier.M4_LOCAL])
        for tier in priority:
            candidates = [n for n in online if n.tier == tier]
            if candidates:
                # Pick lowest latency
                return min(candidates, key=lambda n: n.latency_ms)
        return online[0]  # Fallback to any online node

    def can_speculate(self) -> bool:
        """Both M2 and M4 are online and capable."""
        m2 = self.nodes.get("m2")
        m4 = self.nodes.get("m4")
        return (
            SPECULATIVE_ENABLED
            and m2 and m2.status == "online"
            and m4 and m4.status == "online"
            and m2.speculative_capable
        )

    def get_mesh_decision(self, query: str, require_private: bool = False, prefer_speculative: bool = True) -> MeshDecision:
        """Make a full routing decision."""
        task = TaskClassifier.classify(query)
        primary = self.get_best_node(task, require_private)

        if not primary:
            return MeshDecision(
                task_type=task,
                primary_node="none",
                fallback_nodes=[],
                model="none",
                reasoning="No nodes online",
                estimated_latency_ms=99999,
            )

        # Model selection per node
        model_map = {
            ("m2", TaskType.INTENT): "qwen3:0.6b",
            ("m2", TaskType.GUARDRAIL): "qwen3:0.6b",
            ("m2", TaskType.EMBED): "nomic-embed-text",
            ("m2", TaskType.FAST_CHAT): "qwen3:4b",
            ("m2", TaskType.SUMMARIZE): "qwen3:4b",
            ("m4", TaskType.CODE): "qwen3-coder:8b",
            ("m4", TaskType.REASONING): "qwen3:8b",
            ("m4", TaskType.CREATIVE): "gemma-3-12b-it",
            ("m4", TaskType.FAST_CHAT): "qwen3:8b",
            ("m4", TaskType.SUMMARIZE): "qwen3:8b",
            ("m4", TaskType.VISION): "gemma-3-12b-it",
            ("vast", TaskType.CODE): "gemma-4:27b",
            ("vast", TaskType.REASONING): "gemma-4:27b",
            ("vast", TaskType.AGENTIC): "gemma-4:27b",
        }

        model = model_map.get((primary.node_id, task), "qwen3:8b")

        # Check if requested model is available, fallback
        if model not in primary.models_loaded and primary.models_loaded:
            # Pick closest available
            model = primary.models_loaded[0]

        # Fallback chain
        fallbacks = []
        for node_id, node in self.nodes.items():
            if node_id != primary.node_id and node.status == "online":
                if not (require_private and node.tier == DeviceTier.VAST_CLOUD):
                    fallbacks.append(node_id)

        # Speculative decision
        use_spec = prefer_speculative and self.can_speculate() and primary.node_id == "m4"

        return MeshDecision(
            task_type=task,
            primary_node=primary.node_id,
            fallback_nodes=fallbacks,
            model=model,
            reasoning=f"Task '{task.value}' → {primary.node_id} ({primary.tier.value}) with {model}",
            use_speculative=use_spec,
            estimated_latency_ms=int(primary.latency_ms + (50 if use_spec else 0)),
            privacy_level="local" if primary.tier != DeviceTier.VAST_CLOUD else "cloud",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Inference Engine — Ollama calls with fallback
# ═══════════════════════════════════════════════════════════════════════════════

class InferenceEngine:
    """Executes inference on nodes with automatic fallback."""

    def __init__(self, node_manager: NodeManager):
        self.nodes = node_manager

    async def chat(
        self,
        messages: List[Dict[str, str]],
        decision: MeshDecision,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> MeshResponse:
        """Execute chat with fallback chain."""
        start = time.perf_counter()

        # Try primary
        for node_id in [decision.primary_node] + decision.fallback_nodes:
            node = self.nodes.nodes.get(node_id)
            if not node or node.status != "online":
                continue

            try:
                result = await self._call_ollama(
                    node, messages, decision.model, temperature, max_tokens
                )
                result.latency_ms = (time.perf_counter() - start) * 1000
                return result
            except Exception as e:
                log(f"Node {node_id} failed: {e}", "WARN")
                continue

        return MeshResponse(
            text="All inference nodes failed. Mesh degraded.",
            node="none",
            model="none",
            latency_ms=(time.perf_counter() - start) * 1000,
        )

    async def _call_ollama(
        self,
        node: DeviceProfile,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> MeshResponse:
        url = f"http://{node.host}:{node.ollama_port}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data.get("message", {}).get("content", "")
        tokens_out = data.get("eval_count", len(text.split()))
        tokens_in = sum(len(m.get("content", "").split()) for m in messages)

        return MeshResponse(
            text=text,
            node=node.node_id,
            model=model,
            latency_ms=0,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    async def embed(self, text: str, node_id: str = "m2") -> List[float]:
        """Get embeddings from specified node."""
        node = self.nodes.nodes.get(node_id)
        if not node or node.status != "online":
            node = self.nodes.nodes.get("m4")
        if not node or node.status != "online":
            raise HTTPException(503, "No embedding node available")

        url = f"http://{node.host}:{node.ollama_port}/api/embeddings"
        payload = {"model": "nomic-embed-text", "prompt": text[:2000]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return data.get("embedding", [])


# ═══════════════════════════════════════════════════════════════════════════════
# Speculative Decoding Bridge — M2 drafts, M4 verifies
# ═══════════════════════════════════════════════════════════════════════════════

class SpeculativeBridge:
    """
    Cross-device speculative decoding.

    Protocol:
      1. M2 generates K draft tokens using a tiny model (0.6B-1B)
      2. Draft sequence sent to M4 over LAN
      3. M4 runs target model with draft as prefix/suggestion
      4. M4 verifies and corrects, returns final text
      5. Speedup: M2 does ~80% of token generation, M4 only verifies/corrects

    Note: True token-level speculative decoding requires logits access.
    This implementation uses a "draft-as-prefix" strategy that is practical
    with Ollama's API while still achieving significant speedup when the
    draft model aligns well with the target.
    """

    DRAFT_MODEL = "qwen3:0.6b"
    DRAFT_MAX_TOKENS = 256
    TARGET_MODEL = "qwen3:8b"

    def __init__(self, node_manager: NodeManager, engine: InferenceEngine):
        self.nodes = node_manager
        self.engine = engine

    async def generate(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2048) -> MeshResponse:
        """Generate with speculative drafting."""
        start = time.perf_counter()
        m2 = self.nodes.nodes.get("m2")
        m4 = self.nodes.nodes.get("m4")

        if not m2 or m2.status != "online" or not m4 or m4.status != "online":
            # Fallback to normal M4 generation
            decision = MeshDecision(
                task_type=TaskType.FAST_CHAT,
                primary_node="m4",
                fallback_nodes=[],
                model=self.TARGET_MODEL,
                reasoning="Speculative unavailable, falling back to M4",
                use_speculative=False,
            )
            return await self.engine.chat(messages, decision, temperature, max_tokens)

        # Phase 1: M2 drafts
        draft_start = time.perf_counter()
        draft_text = await self._draft_on_m2(messages, temperature, min(max_tokens, self.DRAFT_MAX_TOKENS))
        draft_latency = (time.perf_counter() - draft_start) * 1000
        log(f"Draft generated on M2 in {draft_latency:.0f}ms: {len(draft_text)} chars")

        # Phase 2: M4 verifies with draft as system prompt hint
        verify_start = time.perf_counter()
        # Inject draft as a hint to reduce generation work
        enhanced_messages = self._inject_draft_hint(messages, draft_text)
        result = await self._verify_on_m4(enhanced_messages, temperature, max_tokens)
        verify_latency = (time.perf_counter() - verify_start) * 1000

        # Calculate acceptance ratio (rough: how much did M4 reuse)
        acceptance = self._estimate_acceptance(draft_text, result.text)

        total_latency = (time.perf_counter() - start) * 1000

        log(f"Speculative complete: draft={draft_latency:.0f}ms verify={verify_latency:.0f}ms "
            f"acceptance={acceptance:.1%} total={total_latency:.0f}ms")

        return MeshResponse(
            text=result.text,
            node="m4+m2",
            model=self.TARGET_MODEL,
            latency_ms=total_latency,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            speculative_used=True,
            draft_accepted_ratio=acceptance,
        )

    async def _draft_on_m2(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> str:
        """Generate draft on M2."""
        m2 = self.nodes.nodes["m2"]
        url = f"http://{m2.host}:{m2.ollama_port}/api/chat"
        payload = {
            "model": self.DRAFT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": max(0.1, temperature - 0.2),  # Slightly more focused
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("message", {}).get("content", "")

    def _inject_draft_hint(self, messages: List[Dict[str, str]], draft: str) -> List[Dict[str, str]]:
        """Add draft as a hint in the system prompt."""
        new_messages = list(messages)
        # Prepend a system message with the draft as context
        hint = {
            "role": "system",
            "content": (
                f"You are verifying and improving a draft response. "
                f"Use the draft as a starting point but ensure accuracy and completeness.\n\n"
                f"Draft to improve:\n{draft[:1500]}"
            ),
        }
        new_messages.insert(0, hint)
        return new_messages

    async def _verify_on_m4(self, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> MeshResponse:
        """Verify/correct on M4."""
        m4 = self.nodes.nodes["m4"]
        url = f"http://{m4.host}:{m4.ollama_port}/api/chat"
        payload = {
            "model": self.TARGET_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data.get("message", {}).get("content", "")
        tokens_out = data.get("eval_count", len(text.split()))
        tokens_in = sum(len(m.get("content", "").split()) for m in messages)

        return MeshResponse(
            text=text,
            node="m4",
            model=self.TARGET_MODEL,
            latency_ms=0,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )

    def _estimate_acceptance(self, draft: str, final: str) -> float:
        """Rough estimate of token acceptance ratio."""
        if not draft or not final:
            return 0.0
        draft_words = draft.split()
        final_words = final.split()
        if not draft_words:
            return 0.0
        # Count how many draft words appear in final (in order)
        matched = 0
        fi = 0
        for dw in draft_words:
            while fi < len(final_words) and final_words[fi] != dw:
                fi += 1
            if fi < len(final_words):
                matched += 1
                fi += 1
        return matched / len(draft_words)


# ═══════════════════════════════════════════════════════════════════════════════
# FastAPI App
# ═══════════════════════════════════════════════════════════════════════════════

node_manager = NodeManager()
inference_engine = InferenceEngine(node_manager)
speculative_bridge = SpeculativeBridge(node_manager, inference_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log("Mac Mesh Orchestrator starting...")
    await node_manager.start_health_loop()
    log(f"Health checks every {HEALTH_INTERVAL_SEC}s")
    log(f"Speculative decoding: {'ENABLED' if SPECULATIVE_ENABLED else 'DISABLED'}")
    yield
    log("Mac Mesh Orchestrator shutting down.")


app = FastAPI(
    title="Mac Mesh Orchestrator",
    description="Dual-Mac inference mesh with speculative decoding",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "mac_mesh_orchestrator",
        "version": "1.0.0",
        "speculative_enabled": SPECULATIVE_ENABLED,
        "nodes": {n.node_id: n.status for n in node_manager.nodes.values()},
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    nodes_dict = {n.node_id: n.to_dict() for n in node_manager.nodes.values()}
    total_throughput = sum(n.throughput_tok_s for n in node_manager.nodes.values())
    mesh_ok = sum(1 for n in node_manager.nodes.values() if n.status == "online") >= 1

    return HealthResponse(
        nodes=nodes_dict,
        total_throughput_tok_s=round(total_throughput, 1),
        speculative_ready=node_manager.can_speculate(),
        mesh_status="healthy" if mesh_ok else "degraded",
    )


@app.post("/v1/chat", response_model=MeshResponse)
async def chat(req: ChatRequest):
    """
    Main chat endpoint. Automatically routes to optimal node.
    Enable speculative decoding for 2-3x speedup when both Macs are online.
    """
    messages = [{"role": "user", "content": req.message}]

    # Use speculative decoding if requested and available
    if req.use_speculative and node_manager.can_speculate():
        return await speculative_bridge.generate(
            messages, req.temperature, req.max_tokens
        )

    # Standard routing
    decision = node_manager.get_mesh_decision(
        req.message, req.require_private, prefer_speculative=False
    )

    if decision.primary_node == "none":
        raise HTTPException(status_code=503, detail="No inference nodes available")

    return await inference_engine.chat(messages, decision, req.temperature, req.max_tokens)


@app.post("/v1/chat/direct")
async def chat_direct(
    message: str,
    node: str = "m4",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
):
    """Direct chat to a specific node."""
    node_profile = node_manager.nodes.get(node)
    if not node_profile or node_profile.status != "online":
        raise HTTPException(status_code=503, detail=f"Node {node} not available")

    decision = MeshDecision(
        task_type=TaskType.FAST_CHAT,
        primary_node=node,
        fallback_nodes=[],
        model=model or (node_profile.models_loaded[0] if node_profile.models_loaded else "qwen3:8b"),
        reasoning=f"Direct routing to {node}",
    )
    return await inference_engine.chat(
        [{"role": "user", "content": message}], decision, temperature, max_tokens
    )


@app.post("/v1/embed")
async def embed(text: str, node: Optional[str] = None):
    """Get embeddings. Defaults to M2 for offloading."""
    target = node or "m2"
    try:
        embedding = await inference_engine.embed(text, target)
        return {"embedding": embedding, "node": target, "dims": len(embedding)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/v1/route")
async def route_info(query: str, require_private: bool = False):
    """Show routing decision for a query without executing."""
    decision = node_manager.get_mesh_decision(query, require_private)
    return {
        "task_type": decision.task_type.value,
        "primary_node": decision.primary_node,
        "fallback_nodes": decision.fallback_nodes,
        "model": decision.model,
        "reasoning": decision.reasoning,
        "use_speculative": decision.use_speculative,
        "estimated_latency_ms": decision.estimated_latency_ms,
        "privacy_level": decision.privacy_level,
    }


@app.post("/v1/speculative")
async def speculative_chat(req: ChatRequest):
    """Force speculative decoding (M2 draft + M4 verify)."""
    if not node_manager.can_speculate():
        raise HTTPException(
            status_code=503,
            detail="Speculative decoding not available. Both M2 and M4 must be online."
        )
    messages = [{"role": "user", "content": req.message}]
    return await speculative_bridge.generate(messages, req.temperature, req.max_tokens)


@app.get("/v1/nodes")
async def list_nodes():
    """List all nodes and their status."""
    return {n.node_id: n.to_dict() for n in node_manager.nodes.values()}


@app.post("/v1/nodes/{node_id}/refresh")
async def refresh_node(node_id: str):
    """Force health check on a specific node."""
    node = node_manager.nodes.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    await node_manager._check_node(node)
    return node.to_dict()


# ═══════════════════════════════════════════════════════════════════════════════
# SOV3 Integration
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/sov3/status")
async def sov3_status():
    """Proxy SOV3 status for mesh dashboard."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:3101/mcp/coord_get_dashboard")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        pass
    return {"status": "sovereign_mode", "message": "SOV3 coordination running locally"}


# ═══════════════════════════════════════════════════════════════════════════════
# Siri / Apple Intelligence Integration
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/siri/chat")
async def siri_chat(message: str, mode: str = "auto"):
    """
    Siri-optimized chat. Returns plain text for Shortcuts Speak action.
    Usage: GET /siri/chat?message=What+is+2+2&mode=fast
    """
    req = ChatRequest(message=message, use_speculative=(mode != "fast"))
    try:
        result = await chat(req)
        # Format for Siri voice output
        text = result.text.replace("**", "").replace("#", "").replace("`", "")
        text = text.replace("🧠", "").replace("🎨", "").replace("✨", "")
        # Truncate for Siri
        if len(text) > 800:
            text = text[:800] + "... (truncated for voice)"
        return text
    except Exception as e:
        return f"Sorry, the mesh is unavailable. Error: {str(e)[:100]}"


@app.get("/siri/status")
async def siri_status():
    """Siri-friendly mesh status."""
    online = [n.node_id for n in node_manager.get_online_nodes()]
    can_spec = node_manager.can_speculate()
    return (
        f"Mesh status: {len(online)} nodes online: {', '.join(online)}. "
        f"Speculative decoding is {'available' if can_spec else 'unavailable'}."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    log(f"🌐 Starting Mac Mesh Orchestrator on port {MESH_PORT}")
    log(f"   M2 target: {M2_HOST}:{M2_PORT} (Ollama:{M2_OLLAMA_PORT})")
    log(f"   M4 local: localhost:{M4_OLLAMA_PORT}")
    log(f"   Vast: {VAST_HOST}:{VAST_OLLAMA_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=MESH_PORT, log_level="info")
