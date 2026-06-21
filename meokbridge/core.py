#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MEOKBRIDGE CORE — Universal Compute & Service Connector                     ║
║                                                                              ║
║  The one bridge to connect them all:                                         ║
║    • MacBooks (M1/M2/M3/M4) via Ollama/MLX                                   ║
║    • PCs (Windows/Linux) via Ollama/llama.cpp/ONNX                           ║
║    • GPUs (NVIDIA/AMD/Intel) via CUDA/ROCm/DirectML                          ║
║    • Cloud instances (Vast/Lambda/RunPod/CoreWeave) via SSH/API              ║
║    • MCP servers (tools, databases, browsers) via stdio/SSE                  ║
║    • A2A agents (peer-to-peer) via HTTP/gRPC                                 ║
║    • APIs (OpenAI, Anthropic, DeepSeek, Qwen) via REST                       ║
║                                                                              ║
║  One config file. One CLI. One API. Infinite connections.                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, AsyncIterator
from pathlib import Path

import httpx


# ═══════════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════════

class NodeType(str, Enum):
    OLLAMA = "ollama"           # Local or remote Ollama instance
    MLX = "mlx"                 # Apple MLX (macOS only)
    LLAMACPP = "llamacpp"       # llama.cpp server
    VLLM = "vllm"               # vLLM server
    OPENAI_API = "openai_api"   # OpenAI-compatible API (any provider)
    MCP = "mcp"                 # Model Context Protocol server
    A2A = "a2a"                 # Agent-to-Agent Protocol peer
    WEBLLM = "webllm"           # Browser-based WebGPU inference
    CUSTOM = "custom"           # Custom HTTP/gRPC endpoint


class NodeStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class NodeCapability:
    """What a node can do."""
    chat: bool = False
    embed: bool = False
    vision: bool = False
    code: bool = False
    reasoning: bool = False
    tool_use: bool = False
    streaming: bool = False
    max_tokens: int = 4096
    context_window: int = 32768
    languages: List[str] = field(default_factory=lambda: ["en"])


@dataclass
class Node:
    """A single node in the MEOKBRIDGE network."""
    id: str
    name: str
    node_type: NodeType
    url: str
    api_key: Optional[str] = None
    models: List[str] = field(default_factory=list)
    capabilities: NodeCapability = field(default_factory=NodeCapability)
    status: NodeStatus = NodeStatus.UNKNOWN
    latency_ms: float = 99999.0
    last_seen: float = 0.0
    priority: int = 0  # Higher = preferred
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # For MCP/A2A
    transport: Optional[str] = None  # "stdio", "sse", "http", "grpc"
    command: Optional[str] = None    # For stdio MCP servers

    def to_dict(self) -> dict:
        d = asdict(self)
        d["node_type"] = self.node_type.value
        d["status"] = self.status.value
        return d

    @property
    def fingerprint(self) -> str:
        """Unique fingerprint for deduplication."""
        return hashlib.sha256(f"{self.node_type}:{self.url}".encode()).hexdigest()[:16]


@dataclass
class BridgeResult:
    """Result from any bridge call."""
    text: str
    node_id: str
    model: str
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CouncilResult:
    """Result from a council chat with tiered parallelism."""
    text: str
    consensus_score: float
    models_consulted: List[str]
    latency_ms: float
    cost_usd: float


# ═══════════════════════════════════════════════════════════════════════════════
# Protocol Adapters — Speak any protocol
# ═══════════════════════════════════════════════════════════════════════════════

class ProtocolAdapter:
    """Base class for protocol adapters."""

    async def health_check(self, node: Node) -> NodeStatus:
        raise NotImplementedError

    async def list_models(self, node: Node) -> List[str]:
        raise NotImplementedError

    async def chat(self, node: Node, messages: List[Dict], **kwargs) -> BridgeResult:
        raise NotImplementedError

    async def embed(self, node: Node, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError


class OllamaAdapter(ProtocolAdapter):
    """Adapter for Ollama API."""

    async def health_check(self, node: Node) -> NodeStatus:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{node.url}/api/tags")
                if resp.status_code == 200:
                    node.models = [m["name"] for m in resp.json().get("models", [])]
                    return NodeStatus.ONLINE
                return NodeStatus.DEGRADED
        except Exception:
            return NodeStatus.OFFLINE

    async def list_models(self, node: Node) -> List[str]:
        return node.models

    async def chat(self, node: Node, messages: List[Dict], **kwargs) -> BridgeResult:
        start = time.perf_counter()
        model = kwargs.get("model", node.models[0] if node.models else "llama3.1")
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048),
            },
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{node.url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.perf_counter() - start) * 1000
        text = data.get("message", {}).get("content", "")
        tokens_out = data.get("eval_count", len(text.split()))
        tokens_in = sum(len(m.get("content", "").split()) for m in messages)

        return BridgeResult(
            text=text,
            node_id=node.id,
            model=model,
            latency_ms=latency,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=0.0,
        )

    async def embed(self, node: Node, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            payload = {"model": "nomic-embed-text", "prompt": text[:2000]}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{node.url}/api/embeddings", json=payload)
                results.append(resp.json().get("embedding", []))
        return results


class OpenAIAdapter(ProtocolAdapter):
    """Adapter for any OpenAI-compatible API."""

    async def health_check(self, node: Node) -> NodeStatus:
        try:
            headers = {"Authorization": f"Bearer {node.api_key}"} if node.api_key else {}
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{node.url}/models", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    node.models = [m["id"] for m in data.get("data", [])]
                    return NodeStatus.ONLINE
                return NodeStatus.DEGRADED
        except Exception:
            return NodeStatus.OFFLINE

    async def list_models(self, node: Node) -> List[str]:
        return node.models

    async def chat(self, node: Node, messages: List[Dict], **kwargs) -> BridgeResult:
        start = time.perf_counter()
        model = kwargs.get("model", node.models[0] if node.models else "gpt-4o")
        headers = {
            "Authorization": f"Bearer {node.api_key}",
            "Content-Type": "application/json",
        } if node.api_key else {"Content-Type": "application/json"}

        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{node.url}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.perf_counter() - start) * 1000
        choice = data.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return BridgeResult(
            text=text,
            node_id=node.id,
            model=model,
            latency_ms=latency,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            cost_usd=0.0,  # Would calculate from pricing table
        )

    async def embed(self, node: Node, texts: List[str]) -> List[List[float]]:
        headers = {"Authorization": f"Bearer {node.api_key}"} if node.api_key else {}
        payload = {"model": "text-embedding-3-small", "input": texts}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{node.url}/embeddings", json=payload, headers=headers)
            data = resp.json()
            return [d["embedding"] for d in data.get("data", [])]


class MCPAdapter(ProtocolAdapter):
    """Adapter for Model Context Protocol servers."""

    async def health_check(self, node: Node) -> NodeStatus:
        # MCP stdio servers are "healthy" if we can spawn the process
        if node.transport == "stdio":
            return NodeStatus.ONLINE if node.command else NodeStatus.OFFLINE
        # SSE/HTTP MCP servers
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(node.url)
                return NodeStatus.ONLINE if resp.status_code == 200 else NodeStatus.OFFLINE
        except Exception:
            return NodeStatus.OFFLINE

    async def list_models(self, node: Node) -> List[str]:
        return ["mcp_tools"]  # MCP servers expose tools, not models

    async def chat(self, node: Node, messages: List[Dict], **kwargs) -> BridgeResult:
        # MCP doesn't do chat directly — tools are called by an LLM
        return BridgeResult(
            text="[MCP server — use tools via an LLM node]",
            node_id=node.id,
            model="mcp",
            latency_ms=0,
        )

    async def embed(self, node: Node, texts: List[str]) -> List[List[float]]:
        return []


class A2AAdapter(ProtocolAdapter):
    """Adapter for Agent-to-Agent Protocol peers."""

    async def health_check(self, node: Node) -> NodeStatus:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{node.url}/.well-known/agent.json")
                return NodeStatus.ONLINE if resp.status_code == 200 else NodeStatus.OFFLINE
        except Exception:
            return NodeStatus.OFFLINE

    async def list_models(self, node: Node) -> List[str]:
        return ["a2a_agent"]

    async def chat(self, node: Node, messages: List[Dict], **kwargs) -> BridgeResult:
        start = time.perf_counter()
        payload = {
            "messages": messages,
            "task": kwargs.get("task", "conversation"),
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{node.url}/tasks/send", json=payload)
            resp.raise_for_status()
            data = resp.json()

        latency = (time.perf_counter() - start) * 1000
        text = data.get("result", {}).get("text", "")

        return BridgeResult(
            text=text,
            node_id=node.id,
            model="a2a_agent",
            latency_ms=latency,
        )

    async def embed(self, node: Node, texts: List[str]) -> List[List[float]]:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# Adapter Registry
# ═══════════════════════════════════════════════════════════════════════════════

ADAPTERS: Dict[NodeType, ProtocolAdapter] = {
    NodeType.OLLAMA: OllamaAdapter(),
    NodeType.MLX: OllamaAdapter(),  # MLX can expose Ollama-compatible API
    NodeType.LLAMACPP: OllamaAdapter(),
    NodeType.VLLM: OpenAIAdapter(),
    NodeType.OPENAI_API: OpenAIAdapter(),
    NodeType.MCP: MCPAdapter(),
    NodeType.A2A: A2AAdapter(),
    NodeType.WEBLLM: OpenAIAdapter(),
    NodeType.CUSTOM: OpenAIAdapter(),
}


# ═══════════════════════════════════════════════════════════════════════════════
# MEOKBRIDGE Core — The Universal Connector
# ═══════════════════════════════════════════════════════════════════════════════

class MeokBridge:
    """
    Universal bridge for connecting any compute or service node.

    Usage:
        bridge = MeokBridge()
        bridge.add_node(Node(id="m4", name="MacBook M4", node_type=NodeType.OLLAMA, url="http://localhost:11434"))
        bridge.add_node(Node(id="vast", name="Vast GPU", node_type=NodeType.OLLAMA, url="http://localhost:11436"))
        bridge.add_node(Node(id="openrouter", name="OpenRouter", node_type=NodeType.OPENAI_API, url="https://openrouter.ai/api/v1", api_key="..."))

        result = await bridge.chat("Explain quantum computing")
        # Automatically routes to best available node
    """

    def __init__(self, config_path: Optional[str] = None):
        self.nodes: Dict[str, Node] = {}
        self._health_task: Optional[asyncio.Task] = None
        self._config_path = config_path or os.path.expanduser("~/.meokbridge/config.yaml")

    def add_node(self, node: Node) -> None:
        """Add a node to the bridge."""
        self.nodes[node.id] = node
        print(f"[MEOKBRIDGE] Added {node.node_type.value}: {node.name} ({node.url})")

    def remove_node(self, node_id: str) -> bool:
        """Remove a node."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            print(f"[MEOKBRIDGE] Removed node: {node_id}")
            return True
        return False

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def list_nodes(self, node_type: Optional[NodeType] = None, status: Optional[NodeStatus] = None) -> List[Node]:
        """List nodes, optionally filtered."""
        result = list(self.nodes.values())
        if node_type:
            result = [n for n in result if n.node_type == node_type]
        if status:
            result = [n for n in result if n.status == status]
        return result

    async def health_check(self, node_id: Optional[str] = None) -> Dict[str, NodeStatus]:
        """Check health of all nodes or a specific node."""
        targets = [self.nodes[node_id]] if node_id else list(self.nodes.values())
        results = {}

        for node in targets:
            adapter = ADAPTERS.get(node.node_type)
            if adapter:
                node.status = await adapter.health_check(node)
                node.last_seen = time.time()
            results[node.id] = node.status

        return results

    async def start_health_loop(self, interval_sec: float = 30.0):
        """Start periodic health checks."""
        async def loop():
            while True:
                await self.health_check()
                await asyncio.sleep(interval_sec)
        self._health_task = asyncio.create_task(loop())

    async def chat(
        self,
        message: str,
        node_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        prefer_local: bool = False,
    ) -> BridgeResult:
        """
        Chat through the bridge. Auto-routes to best node if node_id not specified.

        Routing logic:
        1. If node_id specified → use that node
        2. If prefer_local → pick lowest-latency local node
        3. Otherwise → pick highest-priority online node
        """
        messages = [{"role": "user", "content": message}]

        # Determine target node
        if node_id and node_id in self.nodes:
            target = self.nodes[node_id]
        else:
            target = self._select_best_node(prefer_local=prefer_local)

        if not target:
            return BridgeResult(
                text="No nodes available in MEOKBRIDGE network.",
                node_id="none",
                model="none",
                latency_ms=0,
                error="No nodes available",
            )

        adapter = ADAPTERS.get(target.node_type)
        if not adapter:
            return BridgeResult(
                text=f"No adapter for node type: {target.node_type.value}",
                node_id=target.id,
                model="none",
                latency_ms=0,
            )

        return await adapter.chat(
            target, messages, model=model, temperature=temperature, max_tokens=max_tokens
        )

    def _select_best_node(self, prefer_local: bool = False) -> Optional[Node]:
        """Select the best available node."""
        candidates = [n for n in self.nodes.values() if n.status == NodeStatus.ONLINE]
        if not candidates:
            return None

        # Filter to local-ish nodes if preferred
        if prefer_local:
            local_types = {NodeType.OLLAMA, NodeType.MLX, NodeType.LLAMACPP}
            local_candidates = [n for n in candidates if n.node_type in local_types]
            if local_candidates:
                candidates = local_candidates

        # Sort by priority (desc), then latency (asc)
        candidates.sort(key=lambda n: (-n.priority, n.latency_ms))
        return candidates[0]

    async def embed(self, texts: List[str], node_id: Optional[str] = None) -> List[List[float]]:
        """Get embeddings from best available embedding node."""
        if node_id and node_id in self.nodes:
            target = self.nodes[node_id]
        else:
            candidates = [
                n for n in self.nodes.values()
                if n.status == NodeStatus.ONLINE and n.capabilities.embed
            ]
            if not candidates:
                return []
            target = min(candidates, key=lambda n: n.latency_ms)

        adapter = ADAPTERS.get(target.node_type)
        if not adapter:
            return []
        return await adapter.embed(target, texts)

    async def council_chat(
        self,
        message: str,
        node_ids: Optional[List[str]] = None,
        consensus_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Council mode: query multiple nodes and return consensus.
        Byzantine Fault Tolerant — ignores failed nodes.
        """
        targets = [self.nodes[nid] for nid in node_ids if nid in self.nodes] if node_ids else \
                  [n for n in self.nodes.values() if n.status == NodeStatus.ONLINE and n.node_type not in {NodeType.MCP, NodeType.A2A}]

        if len(targets) < 2:
            # Fall back to single best node
            result = await self.chat(message)
            return {
                "consensus_text": result.text,
                "consensus_score": 1.0,
                "responses": [{"node": result.node_id, "text": result.text}],
                "total_nodes": 1,
                "failed_nodes": 0,
            }

        # Query all nodes in parallel
        async def query_node(node: Node) -> Optional[BridgeResult]:
            try:
                adapter = ADAPTERS.get(node.node_type)
                if not adapter:
                    return None
                return await adapter.chat(node, [{"role": "user", "content": message}])
            except Exception:
                return None

        results = await asyncio.gather(*[query_node(n) for n in targets])
        valid_results = [r for r in results if r is not None]

        # Simple consensus: pick the most common response (by first 100 chars hash)
        from collections import Counter
        hashes = [hashlib.sha256(r.text[:200].encode()).hexdigest()[:8] for r in valid_results]
        most_common_hash, count = Counter(hashes).most_common(1)[0] if hashes else ("", 0)
        consensus_score = count / len(targets) if targets else 0

        consensus_text = next(r.text for r in valid_results if hashlib.sha256(r.text[:200].encode()).hexdigest()[:8] == most_common_hash) if valid_results else "No consensus."

        return {
            "consensus_text": consensus_text,
            "consensus_score": consensus_score,
            "responses": [{"node": r.node_id, "text": r.text[:300], "model": r.model} for r in valid_results],
            "total_nodes": len(targets),
            "failed_nodes": len(targets) - len(valid_results),
            "total_latency_ms": sum(r.latency_ms for r in valid_results),
            "total_cost_usd": sum(r.cost_usd for r in valid_results),
        }

    async def council_chat_fast(
        self,
        message: str,
        node_ids: Optional[List[str]] = None,
        consensus_threshold: float = 0.7,
    ) -> CouncilResult:
        """
        Council mode with tiered parallel gather.
        Tier 1: 3 fastest local / fast-free-tier models with 5s timeout.
        Tier 2: remaining models with 15s timeout if Tier 1 consensus < threshold.
        """
        targets = [self.nodes[nid] for nid in node_ids if nid in self.nodes] if node_ids else \
                  [n for n in self.nodes.values() if n.status == NodeStatus.ONLINE and n.node_type not in {NodeType.MCP, NodeType.A2A}]

        if len(targets) < 2:
            result = await self.chat(message)
            return CouncilResult(
                text=result.text,
                consensus_score=1.0,
                models_consulted=[result.model],
                latency_ms=result.latency_ms,
                cost_usd=result.cost_usd,
            )

        fast_model_keywords = {
            "deepseek-v4-flash", "owl-alpha", "gemma4-27b", "gemma-4-27b",
        }

        def is_fast_node(node: Node) -> bool:
            if node.node_type in {NodeType.OLLAMA, NodeType.MLX, NodeType.LLAMACPP}:
                return True
            for m in node.models:
                m_lower = m.lower()
                for kw in fast_model_keywords:
                    if kw in m_lower:
                        return True
            for tag in node.tags:
                tag_lower = tag.lower()
                for kw in fast_model_keywords:
                    if kw in tag_lower:
                        return True
            return False

        tier1_candidates = [n for n in targets if is_fast_node(n)]
        tier2_candidates = [n for n in targets if n not in tier1_candidates]

        tier1_candidates.sort(key=lambda n: n.latency_ms)
        tier1_nodes = tier1_candidates[:3]

        if not tier1_nodes:
            all_sorted = sorted(targets, key=lambda n: n.latency_ms)
            tier1_nodes = all_sorted[:3]
            tier2_candidates = [n for n in targets if n not in tier1_nodes]

        messages = [{"role": "user", "content": message}]

        async def query_with_timeout(node: Node, timeout: float) -> Optional[BridgeResult]:
            try:
                adapter = ADAPTERS.get(node.node_type)
                if not adapter:
                    return None
                return await asyncio.wait_for(
                    adapter.chat(node, messages),
                    timeout=timeout,
                )
            except Exception:
                return None

        start = time.perf_counter()

        # Tier 1 — fast path
        tier1_results = await asyncio.gather(*[query_with_timeout(n, 5.0) for n in tier1_nodes])
        tier1_valid = [r for r in tier1_results if r is not None]

        from collections import Counter

        def _consensus(results: List[BridgeResult], denominator: int) -> tuple[str, float]:
            if not results or denominator == 0:
                return "No consensus.", 0.0
            hashes = [hashlib.sha256(r.text[:200].encode()).hexdigest()[:8] for r in results]
            most_common_hash, count = Counter(hashes).most_common(1)[0]
            score = count / denominator
            text = next(r.text for r in results if hashlib.sha256(r.text[:200].encode()).hexdigest()[:8] == most_common_hash)
            return text, score

        consensus_text, consensus_score = _consensus(tier1_valid, len(tier1_nodes))

        if consensus_score >= consensus_threshold:
            total_latency = (time.perf_counter() - start) * 1000
            return CouncilResult(
                text=consensus_text,
                consensus_score=consensus_score,
                models_consulted=[r.model for r in tier1_valid],
                latency_ms=total_latency,
                cost_usd=sum(r.cost_usd for r in tier1_valid),
            )

        # Tier 2 — broad gather
        tier2_results = await asyncio.gather(*[query_with_timeout(n, 15.0) for n in tier2_candidates])
        tier2_valid = [r for r in tier2_results if r is not None]

        all_valid = tier1_valid + tier2_valid
        total_latency = (time.perf_counter() - start) * 1000

        if not all_valid:
            return CouncilResult(
                text="No consensus.",
                consensus_score=0.0,
                models_consulted=[],
                latency_ms=total_latency,
                cost_usd=0.0,
            )

        consensus_text, consensus_score = _consensus(all_valid, len(targets))

        return CouncilResult(
            text=consensus_text,
            consensus_score=consensus_score,
            models_consulted=[r.model for r in all_valid],
            latency_ms=total_latency,
            cost_usd=sum(r.cost_usd for r in all_valid),
        )

    def to_dict(self) -> dict:
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "node_count": len(self.nodes),
            "online_count": len([n for n in self.nodes.values() if n.status == NodeStatus.ONLINE]),
        }
