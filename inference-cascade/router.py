"""Cascade Router — The brain of MEOKCLAW's split-inference architecture.

Every query passes through L0 intent classification, then gets routed
to the smallest capable model tier (L1-L3) or external tool/MCP/A2A.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, AsyncIterator

from .device_profile import DeviceProfile
from .model_registry import ModelRegistry, ModelCapability


class InferenceTier(Enum):
    L0_ROUTER = "l0"      # Intent classification only
    L1_EDGE = "l1"        # On-device small model (1-4B)
    L2_LOCAL = "l2"       # Edge/large local model (7-27B)
    L3_CLOUD = "l3"       # Cloud API (100B+)
    TOOL = "tool"         # MCP/A2A tool execution
    HYBRID = "hybrid"     # Multi-turn: L1 for chat, L3 for reasoning


@dataclass
class RoutingDecision:
    tier: InferenceTier
    model_id: str
    reasoning: str
    estimated_latency_ms: int
    privacy_level: str  # "local", "edge", "cloud"
    fallbacks: List[str] = field(default_factory=list)


@dataclass
class CascadeResult:
    text: str
    tier_used: InferenceTier
    model_id: str
    latency_ms: int
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: List[Dict] = field(default_factory=list)
    streaming: bool = False


class CascadeRouter:
    """Routes queries to optimal inference tier."""

    # L0: Intent keywords for fast routing without LLM call
    INTENT_PATTERNS = {
        "coding": ["write code", "function", "class", "import", "def ", "const ", "let ", "var "],
        "math": ["calculate", "solve", "equation", "derivative", "integral", "= ?", "math"],
        "creative": ["write a story", "poem", "song", "creative", "imagine", "fantasy"],
        "summarize": ["summarize", "tl;dr", "key points", "main idea", "brief"],
        "translate": ["translate", "in chinese", "in spanish", "日本語", "中文", "한국어"],
        "image": ["image", "picture", "photo", "draw", "generate image", "create an image"],
        "search": ["search", "find", "look up", "google", "what is", "who is", "when did"],
        "agentic": ["use tool", "call mcp", "delegate", "run command", "browse", "click"],
    }

    # Capability scores: which tiers can handle which intents
    TIER_CAPABILITIES = {
        InferenceTier.L1_EDGE: ["summarize", "translate", "search", "chat", "greeting"],
        InferenceTier.L2_LOCAL: ["coding", "math", "creative", "summarize", "translate", "search", "chat"],
        InferenceTier.L3_CLOUD: ["coding", "math", "creative", "summarize", "translate", "search", "chat", "image", "agentic"],
    }

    def __init__(self, device: Optional[DeviceProfile] = None):
        self.device = device or DeviceProfile()
        self.registry = ModelRegistry()
        self._l0_model = None  # Tiny router model (optional)
        self._inference_handlers: Dict[InferenceTier, Callable] = {}

    def register_handler(self, tier: InferenceTier, handler: Callable):
        """Register an async handler for a specific tier."""
        self._inference_handlers[tier] = handler

    def _classify_intent(self, query: str) -> str:
        """L0: Fast keyword-based intent classification (no LLM)."""
        query_lower = query.lower()
        scores = {}
        for intent, keywords in self.INTENT_PATTERNS.items():
            scores[intent] = sum(1 for kw in keywords if kw in query_lower)
        best = max(scores, key=scores.get, default="chat")
        return best if scores[best] > 0 else "chat"

    def _select_tier(self, intent: str, query_len: int, require_private: bool = False) -> InferenceTier:
        """Select optimal tier based on intent, query complexity, and device."""
        # Privacy-first: always local if requested
        if require_private:
            if self.device.has_npu and intent in self.TIER_CAPABILITIES[InferenceTier.L1_EDGE]:
                return InferenceTier.L1_EDGE
            if self.device.has_gpu and intent in self.TIER_CAPABILITIES[InferenceTier.L2_LOCAL]:
                return InferenceTier.L2_LOCAL
            return InferenceTier.L2_LOCAL  # Fallback to best local

        # Simple queries → L1
        if intent in self.TIER_CAPABILITIES[InferenceTier.L1_EDGE] and query_len < 500:
            if self.device.has_npu or self.device.ram_gb >= 8:
                return InferenceTier.L1_EDGE

        # Code/math/creative → L2 or L3
        if intent in ["coding", "math", "creative"]:
            if self.device.has_gpu and self.device.vram_gb >= 8:
                return InferenceTier.L2_LOCAL
            return InferenceTier.L3_CLOUD

        # Agentic/tool use → L3 (or L2 if local tools)
        if intent == "agentic":
            return InferenceTier.TOOL

        # Image generation → L3 (cloud API with image models)
        if intent == "image":
            return InferenceTier.L3_CLOUD

        # Default: try L1, fallback to L2/L3
        if self.device.has_npu:
            return InferenceTier.L1_EDGE
        if self.device.has_gpu:
            return InferenceTier.L2_LOCAL
        return InferenceTier.L3_CLOUD

    async def route(self, query: str, require_private: bool = False, stream: bool = False) -> CascadeResult:
        """Route a query through the cascade and return result."""
        start = time.time()
        intent = self._classify_intent(query)
        tier = self._select_tier(intent, len(query), require_private)

        # Try primary tier
        handler = self._inference_handlers.get(tier)
        if handler:
            try:
                result = await handler(query, stream=stream)
                result.latency_ms = int((time.time() - start) * 1000)
                return result
            except Exception as e:
                # Fallback chain
                for fallback_tier in [InferenceTier.L2_LOCAL, InferenceTier.L3_CLOUD]:
                    if fallback_tier != tier:
                        handler = self._inference_handlers.get(fallback_tier)
                        if handler:
                            result = await handler(query, stream=stream)
                            result.latency_ms = int((time.time() - start) * 1000)
                            result.tier_used = fallback_tier
                            return result
                raise

        # No handler registered — return routing decision for external execution
        return CascadeResult(
            text="",
            tier_used=tier,
            model_id=self.registry.get_default_model(tier),
            latency_ms=int((time.time() - start) * 1000),
        )

    async def route_stream(self, query: str, require_private: bool = False) -> AsyncIterator[str]:
        """Stream tokens from the routed tier."""
        intent = self._classify_intent(query)
        tier = self._select_tier(intent, len(query), require_private)
        handler = self._inference_handlers.get(tier)
        if handler and hasattr(handler, '__call__'):
            # If handler supports streaming, yield from it
            async for token in handler(query, stream=True):
                yield token
        else:
            yield "[No streaming handler registered for tier: {}]".format(tier.value)

    def get_decision(self, query: str, require_private: bool = False) -> RoutingDecision:
        """Get routing decision without executing inference."""
        intent = self._classify_intent(query)
        tier = self._select_tier(intent, len(query), require_private)
        model_id = self.registry.get_default_model(tier)

        latency_map = {
            InferenceTier.L1_EDGE: 80,
            InferenceTier.L2_LOCAL: 300,
            InferenceTier.L3_CLOUD: 2000,
            InferenceTier.TOOL: 500,
        }

        return RoutingDecision(
            tier=tier,
            model_id=model_id,
            reasoning=f"Intent '{intent}' → {tier.value} based on device {self.device}",
            estimated_latency_ms=latency_map.get(tier, 1000),
            privacy_level="local" if tier in (InferenceTier.L1_EDGE, InferenceTier.L2_LOCAL) else "cloud",
            fallbacks=[t.value for t in [InferenceTier.L2_LOCAL, InferenceTier.L3_CLOUD] if t != tier],
        )
