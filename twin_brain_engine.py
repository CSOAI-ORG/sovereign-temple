"""
Twin Brain Engine — M2 drafts fast, M4 verifies deep
Sovereign speculative decoding across the mesh
"""
from __future__ import annotations

import asyncio
import time
from typing import Dict, Any, Optional
import httpx


class TwinBrainEngine:
    """
    Twin Brain: Two-node speculative decoding.
    M2 (draft node) generates fast with tiny model.
    M4 (verify node) validates and completes with large model.
    """

    def __init__(
        self,
        draft_url: str = "http://192.168.50.176:11434",
        verify_url: str = "http://localhost:11434",
        draft_model: str = "qwen3:0.6b",
        verify_model: str = "qwen3:8b",
    ):
        self.draft_url = draft_url.rstrip("/")
        self.verify_url = verify_url.rstrip("/")
        self.draft_model = draft_model
        self.verify_model = verify_model
        self._client = httpx.AsyncClient(timeout=30.0)

    async def generate(
        self,
        prompt: str,
        draft_max_tokens: int = 64,
        verify_max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Full twin-brain generation pipeline."""
        start = time.time()

        # Phase 1: Fast draft from M2
        draft_start = time.time()
        draft = await self._draft(prompt, draft_max_tokens, temperature)
        draft_latency = (time.time() - draft_start) * 1000

        if draft is None:
            # Fallback: single-node generation on M4
            return await self._fallback_generate(prompt, verify_max_tokens, temperature, start)

        # Phase 2: Deep verify from M4 (with draft as hint)
        verify_start = time.time()
        verified = await self._verify(prompt, draft, verify_max_tokens, temperature)
        verify_latency = (time.time() - verify_start) * 1000

        total_latency = (time.time() - start) * 1000

        # Determine if draft was accepted (verified text starts with draft)
        draft_accepted = verified.startswith(draft[:50]) if verified else False

        return {
            "text": verified or draft,
            "draft": draft,
            "draft_accepted": draft_accepted,
            "draft_latency_ms": round(draft_latency, 1),
            "verify_latency_ms": round(verify_latency, 1),
            "total_latency_ms": round(total_latency, 1),
            "cost_usd": 0.0,
            "draft_node": "m2-sidekick",
            "verify_node": "m4-local",
            "draft_model": self.draft_model,
            "verify_model": self.verify_model,
        }

    async def _draft(self, prompt: str, max_tokens: int, temperature: float) -> Optional[str]:
        """Generate fast draft on M2 via /api/chat (Qwen3+ models return empty via /api/generate)."""
        try:
            resp = await self._client.post(
                f"{self.draft_url}/api/chat",
                json={
                    "model": self.draft_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                    },
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception:
            return None

    async def _verify(self, prompt: str, draft: str, max_tokens: int, temperature: float) -> Optional[str]:
        """Verify and complete on M4 using draft as system hint."""
        try:
            system_hint = (
                f"You are MEOKCLAW Twin Brain — the verifier hemisphere. "
                f"A draft assistant proposed this starting point:\n\n{draft[:200]}\n\n"
                f"Review, correct, and complete the response with higher quality."
            )
            resp = await self._client.post(
                f"{self.verify_url}/api/chat",
                json={
                    "model": self.verify_model,
                    "messages": [
                        {"role": "system", "content": system_hint},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max(128, max_tokens),  # Qwen3 needs tokens for thinking
                    },
                },
                timeout=25.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
        except Exception:
            return None

    async def _fallback_generate(self, prompt: str, max_tokens: int, temperature: float, start_time: float) -> Dict[str, Any]:
        """Fallback to single-node when M2 is down."""
        try:
            resp = await self._client.post(
                f"{self.verify_url}/api/chat",
                json={
                    "model": self.verify_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("message", {}).get("content", "").strip()
            latency = (time.time() - start_time) * 1000
            return {
                "text": text,
                "draft": None,
                "draft_accepted": False,
                "draft_latency_ms": 0,
                "verify_latency_ms": round(latency, 1),
                "total_latency_ms": round(latency, 1),
                "cost_usd": 0.0,
                "draft_node": None,
                "verify_node": "m4-local",
                "fallback": True,
            }
        except Exception as e:
            return {
                "text": f"[Twin Brain Error: {e}]",
                "draft": None,
                "draft_accepted": False,
                "error": str(e),
            }

    async def close(self):
        await self._client.aclose()
