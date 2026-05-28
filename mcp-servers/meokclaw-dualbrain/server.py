#!/usr/bin/env python3
"""
MEOKCLAW Dual-Brain MCP Server
Expose sovereign AI orchestration via Model Context Protocol.

Tools:
- meokclaw_think: Single-query dual-brain inference
- meokclaw_council: Multi-model debate with BFT consensus
- meokclaw_quantman: Nested dual-brain reasoning (HY3 convergence)
- meokclaw_guardrails_check: Safety check text against neural guardrails
- meokclaw_model_health: Report on model latency/error health
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from fastmcp import FastMCP, Context
import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MEOK_API_BASE = os.environ.get("MEOK_API_URL", "http://localhost:3201")
DEFAULT_TIMEOUT = float(os.environ.get("MEOK_TIMEOUT", "60"))

mcp = FastMCP(
    "meokclaw-dualbrain",
    instructions=(
        "MEOKCLAW Dual-Brain Orchestration MCP Server. "
        "Route queries through sovereign dual-hemisphere AI with full cost transparency, "
        "guardrails, and multi-model consensus."
    ),
)

# ---------------------------------------------------------------------------
# Shared HTTP client
# ---------------------------------------------------------------------------
_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
    return _client


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
async def meokclaw_think(
    query: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    locale: str = "en",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    Run a single query through the MEOKCLAW dual-brain orchestrator.

    The orchestrator routes to the optimal hemisphere (left: API models,
    right: local models) with automatic fallback chains and guardrails.

    Args:
        query: The user question or task.
        temperature: Sampling temperature (0.0–1.5).
        max_tokens: Maximum tokens to generate.
        locale: Language/locale code (e.g. 'en', 'zh', 'ja').
    """
    if ctx:
        await ctx.info(f"Thinking: {query[:80]}...")

    client = await _get_client()
    payload = {
        "query": query,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "locale": locale,
    }
    resp = await client.post(f"{MEOK_API_BASE}/api/dual-brain", json=payload)
    resp.raise_for_status()
    data = resp.json()

    return {
        "response": data.get("response", ""),
        "model": data.get("model", "unknown"),
        "cost_usd": data.get("cost_usd"),
        "latency_ms": data.get("latency_ms"),
        "hemisphere": data.get("hemisphere"),
        "guardrails_passed": data.get("guardrails_passed", True),
    }


@mcp.tool()
async def meokclaw_council(
    query: str,
    models: list[str] | None = None,
    consensus_threshold: float = 0.66,
    locale: str = "en",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    Convene a Byzantine Council of multiple AI models for consensus.

    Each model independently answers, then a BFT consensus algorithm
    aggregates the responses. Returns the winning answer plus minority
    reports.

    Args:
        query: The question or task for the council.
        models: List of model IDs to convene (default: auto-select 5).
        consensus_threshold: Fraction required for consensus (0.5–1.0).
        locale: Language/locale code.
    """
    if ctx:
        await ctx.info(f"Council convened: {query[:80]}...")

    client = await _get_client()
    payload = {
        "query": query,
        "models": models or ["auto"],
        "consensus_threshold": consensus_threshold,
        "locale": locale,
    }
    resp = await client.post(f"{MEOK_API_BASE}/api/council", json=payload)
    resp.raise_for_status()
    data = resp.json()

    return {
        "consensus_answer": data.get("consensus_answer", ""),
        "confidence": data.get("confidence", 0.0),
        "votes": data.get("votes", []),
        "minority_reports": data.get("minority_reports", []),
        "total_cost_usd": data.get("total_cost_usd"),
    }


@mcp.tool()
async def meokclaw_quantman(
    query: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    locale: str = "en",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    Run QuantMan nested dual-brain reasoning with HY3 convergence.

    QuantMan orchestrates left/right hemisphere meshes, mediates through
    SOV3, and converges on a unified answer. Best for complex reasoning
    requiring multi-perspective analysis.

    Args:
        query: The complex reasoning task.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens.
        locale: Language/locale code.
    """
    if ctx:
        await ctx.info(f"QuantMan reasoning: {query[:80]}...")

    client = await _get_client()
    payload = {
        "query": query,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "locale": locale,
    }
    resp = await client.post(f"{MEOK_API_BASE}/api/quantman", json=payload)
    resp.raise_for_status()
    data = resp.json()

    return {
        "response": data.get("response", ""),
        "left_model": data.get("left_model"),
        "right_model": data.get("right_model"),
        "sov3_mediation": data.get("sov3_mediation"),
        "hy3_convergence": data.get("hy3_convergence"),
        "cost_usd": data.get("cost_usd"),
    }


@mcp.tool()
async def meokclaw_guardrails_check(
    text: str,
    locale: str = "en",
) -> dict[str, Any]:
    """
    Check text against MEOKCLAW neural guardrails.

    Returns violations, severity, and cleaned text if PII redaction
    is triggered. Checks for prompt injection, PII leakage, content
    policy violations, and encoding attacks.

    Args:
        text: The text to evaluate.
        locale: Language/locale code.
    """
    client = await _get_client()
    payload = {"text": text, "locale": locale}
    resp = await client.post(f"{MEOK_API_BASE}/api/guardrails/check", json=payload)
    resp.raise_for_status()
    data = resp.json()

    return {
        "blocked": data.get("blocked", False),
        "violations": data.get("violations", []),
        "cleaned_text": data.get("cleaned_text", text),
        "severity": data.get("severity", "none"),
    }


@mcp.tool()
async def meokclaw_model_health() -> dict[str, Any]:
    """
    Report health status of all configured inference models.

    Returns per-model success rate, P50/P95 latency, and error counts.
    Useful for debugging model outages or slowdowns.
    """
    client = await _get_client()
    resp = await client.get(f"{MEOK_API_BASE}/api/model-health")
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
