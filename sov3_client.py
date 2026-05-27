"""
SOV3 Neural Client — Wire trained models into live pipeline.
Uses /neural/predict endpoint on SOV3 MCP server (port 3101).
"""
from __future__ import annotations

import asyncio
import httpx
from typing import Dict, Any, Optional
from dataclasses import dataclass

SOV3_BASE = "http://localhost:3101"


@dataclass
class ThreatScore:
    score: float  # 0.0 - 1.0
    labels: Dict[str, float]
    blocked: bool


@dataclass
class CareScore:
    burnout_risk: float
    care_imbalance: float
    compassion_fatigue: float
    sustainability: float
    overall: float


@dataclass
class PartnershipScore:
    score: float  # 0.0 - 1.0
    agreement_level: str


class SOV3Client:
    """Client for SOV3 neural model inference via /neural/predict."""

    def __init__(self, base_url: str = SOV3_BASE, timeout: float = 3.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def _predict(self, model_type: str, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call SOV3 /neural/predict. Returns None if SOV3 down."""
        try:
            resp = await self._client.post(
                f"{self.base_url}/neural/predict",
                json={"model": model_type, "features": features},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    async def check_threat(self, text: str) -> Optional[ThreatScore]:
        """Call threat_detection. Returns None if SOV3 down."""
        data = await self._predict("threat_detection", {"text": text[:2000]})
        if not data or "error" in data:
            return None
        score = data.get("score", 0.0)
        return ThreatScore(
            score=score,
            labels=data.get("threat_scores", {"overall": score}),
            blocked=score > 0.5,
        )

    async def score_care(self, text: str) -> Optional[CareScore]:
        """Call care_validation for output quality scoring."""
        data = await self._predict("care_validation", {"text": text[:2000]})
        if not data or "error" in data:
            return None
        score = data.get("score", 0.5)
        return CareScore(
            burnout_risk=1.0 - score,
            care_imbalance=0.5,
            compassion_fatigue=0.5,
            sustainability=score,
            overall=score,
        )

    async def score_partnership(self, left_text: str, right_text: str) -> Optional[PartnershipScore]:
        """Call partnership detection to score agreement between two outputs."""
        data = await self._predict("partnership_detection", {
            "text_a": left_text[:1500],
            "text_b": right_text[:1500],
            "task_type": "dual_brain_convergence",
        })
        if not data or "error" in data:
            return None
        # Registry model returns "opportunity_score"; fallback returns "score"
        score = data.get("score") or data.get("opportunity_score", 0.5)
        level = "strong" if score > 0.7 else "partial" if score > 0.3 else "weak"
        return PartnershipScore(score=score, agreement_level=level)

    async def close(self):
        await self._client.aclose()
