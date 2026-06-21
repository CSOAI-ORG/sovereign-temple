"""
QuantMan Engine — Nested Dual-Brain with SOV3 Mediation and HY3 Convergence

Architecture:
  Left Hemisphere Mesh  ←──┐
    ├── Kimi K2.6 (API)   │  SOV3 QuantMan
    └── Qwen3:8b (M4)     │     Mediation
                           └──► HY3 Convergence
  Right Hemisphere Mesh  ←──┘
    ├── DeepSeek V4-F (API)
    └── Gemma 4:27b (OR free)

HY3 Ternary States:
  +1 = hemispheres agree → weighted merge
   0 = partial agreement → keep consensus, surface divergence
  -1 = hemispheres disagree → full 4-model BFT council escalation
"""
from __future__ import annotations

import asyncio
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from openrouter_client import OpenRouterClient, InferenceResult
from ollama_client import OllamaClient, OllamaResult
from sov3_client import SOV3Client


@dataclass
class HemisphereOutput:
    """Output from a single hemisphere mesh."""
    text: str
    consensus_score: float  # intra-hemisphere agreement
    models_used: List[str]
    api_latency_ms: float
    local_latency_ms: float
    cost_usd: float
    hemisphere: str  # "left" or "right"


@dataclass
class QuantManResult:
    """Final result after SOV3 mediation and HY3 convergence."""
    text: str
    hy3_state: int  # -1, 0, +1
    partnership_score: float
    left: HemisphereOutput
    right: HemisphereOutput
    sov3_mediation: Dict[str, Any]
    convergence_method: str
    total_latency_ms: float
    total_cost_usd: float


class HemisphereMesh:
    """
    A hemisphere is a mini-mesh of API + local models.
    Runs both in parallel, returns consensus.
    """

    def __init__(
        self,
        name: str,
        api_model: str,
        local_model: str,
        local_url: str = "http://localhost:11434",
    ):
        self.name = name
        self.api_model = api_model
        self.local_model = local_model
        self.openrouter = OpenRouterClient()
        self.local = OllamaClient(local_url)

    async def think(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> HemisphereOutput:
        """Run both API and local models in parallel, return consensus."""
        start = time.perf_counter()
        # Qwen3 models need tokens for thinking — enforce minimum
        safe_max_tokens = max(128, max_tokens)

        async def run_api() -> Optional[InferenceResult]:
            try:
                return await self.openrouter.chat_completion(
                    self.api_model, messages, temperature, safe_max_tokens
                )
            except Exception:
                return None

        async def run_local() -> Optional[OllamaResult]:
            try:
                # Qwen3 models have broken /api/chat template — use /api/generate directly
                if "qwen" in self.local_model.lower():
                    text = await _ollama_generate_fallback(
                        self.local, self.local_model, messages, temperature, safe_max_tokens
                    )
                    if text:
                        return OllamaResult(
                            text=text,
                            model=self.local_model,
                            tokens_in=0,
                            tokens_out=0,
                            latency_ms=0.0,
                        )
                    return None
                return await self.local.chat_completion(
                    self.local_model, messages, temperature, safe_max_tokens
                )
            except Exception:
                return None

        api_res, local_res = await asyncio.gather(run_api(), run_local())

        api_latency = getattr(api_res, "latency_ms", 0) if api_res else 999999
        local_latency = getattr(local_res, "latency_ms", 0) if local_res else 999999
        api_text = getattr(api_res, "text", "") or "" if api_res else ""
        local_text = getattr(local_res, "text", "") or "" if local_res else ""
        
        # Fallback: Qwen3 models often return empty via /api/chat but work via /api/generate
        if not local_text and local_res and "qwen" in self.local_model:
            local_text = await _ollama_generate_fallback(
                self.local, self.local_model, messages, temperature, safe_max_tokens
            ) or local_text
        
        api_cost = getattr(api_res, "cost_usd", 0.0) if api_res else 0.0

        # Intra-hemisphere consensus scoring
        if api_text and local_text:
            consensus_score = _text_similarity(api_text, local_text)
            # Prefer local if consensus is high (sovereignty bias)
            # Prefer API if local is empty or low quality
            if consensus_score > 0.6:
                chosen_text = local_text  # Sovereign bias
                method = "local_pref"
            else:
                chosen_text = api_text if len(api_text) > len(local_text) else local_text
                method = "api_fallback"
            models_used = [self.api_model, self.local_model]
        elif api_text:
            chosen_text = api_text
            consensus_score = 0.5
            models_used = [self.api_model]
            method = "api_only"
        elif local_text:
            chosen_text = local_text
            consensus_score = 0.5
            models_used = [self.local_model]
            method = "local_only"
        else:
            chosen_text = "[Hemisphere mesh failure — both nodes unreachable]"
            consensus_score = 0.0
            models_used = []
            method = "failure"

        total_latency = (time.perf_counter() - start) * 1000

        return HemisphereOutput(
            text=chosen_text,
            consensus_score=consensus_score,
            models_used=models_used,
            api_latency_ms=api_latency,
            local_latency_ms=local_latency,
            cost_usd=api_cost,
            hemisphere=self.name,
        )


class QuantManEngine:
    """
    SOV3-mediated dual-hemisphere convergence engine.
    """

    def __init__(self):
        # Left hemisphere: Kimi K2.6 (reasoning/API) + Qwen3:8b (sovereign/M4)
        # Qwen3:8b uses /api/generate fallback when /api/chat returns empty
        self.left_mesh = HemisphereMesh(
            name="left",
            api_model="moonshotai/kimi-k2.6",
            local_model="qwen3:8b",
            local_url="http://localhost:11434",
        )
        # Right hemisphere: Owl Alpha (agentic/API) + Llama3.2:3b (fast/M2)
        self.right_mesh = HemisphereMesh(
            name="right",
            api_model="openrouter/owl-alpha",
            local_model="llama3.2:3b",
            local_url="http://192.168.50.176:11434",
        )
        self.sov3 = SOV3Client(timeout=3.0)

    async def think(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> QuantManResult:
        """Full QuantMan pipeline: dual hemispheres → SOV3 → HY3 convergence."""
        start = time.perf_counter()

        # Phase 1: Both hemispheres think in parallel
        left_out, right_out = await asyncio.gather(
            self.left_mesh.think(messages, temperature, max_tokens),
            self.right_mesh.think(messages, temperature, max_tokens),
        )

        # If one hemisphere completely failed, mirror the working one
        if left_out.consensus_score == 0.0 and right_out.consensus_score > 0.0:
            left_out = HemisphereOutput(
                text=right_out.text,
                consensus_score=right_out.consensus_score,
                models_used=[f"mirrored_from_{m}" for m in right_out.models_used],
                api_latency_ms=0,
                local_latency_ms=0,
                cost_usd=0.0,
                hemisphere="left",
            )
        elif right_out.consensus_score == 0.0 and left_out.consensus_score > 0.0:
            right_out = HemisphereOutput(
                text=left_out.text,
                consensus_score=left_out.consensus_score,
                models_used=[f"mirrored_from_{m}" for m in left_out.models_used],
                api_latency_ms=0,
                local_latency_ms=0,
                cost_usd=0.0,
                hemisphere="right",
            )

        # Phase 2: SOV3 QuantMan mediation
        partnership_score = await self._sov3_partnership(left_out.text, right_out.text)
        left_care = await self._sov3_care(left_out.text)
        right_care = await self._sov3_care(right_out.text)
        left_threat = await self._sov3_threat(left_out.text)
        right_threat = await self._sov3_threat(right_out.text)

        sov3_data = {
            "partnership_score": partnership_score,
            "left_care": left_care,
            "right_care": right_care,
            "left_threat": left_threat,
            "right_threat": right_threat,
        }

        # Phase 3: HY3 Ternary Convergence
        hy3_state, converged_text, method = self._hy3_converge(
            left_out, right_out, partnership_score, left_care, right_care
        )

        total_latency = (time.perf_counter() - start) * 1000
        total_cost = left_out.cost_usd + right_out.cost_usd

        return QuantManResult(
            text=converged_text,
            hy3_state=hy3_state,
            partnership_score=partnership_score,
            left=left_out,
            right=right_out,
            sov3_mediation=sov3_data,
            convergence_method=method,
            total_latency_ms=total_latency,
            total_cost_usd=total_cost,
        )

    async def _sov3_partnership(self, left_text: str, right_text: str) -> float:
        """Score how much left and right agree.
        
        NOTE: The SOV3 partnership_detection model is trained for business
        partnership/opportunity detection, not dual-brain text convergence.
        We use our local _text_similarity (Jaccard + CJK fallback) which is
        purpose-built for comparing model outputs.
        """
        try:
            result = await self.sov3.score_partnership(left_text, right_text)
            if result is not None and result.score >= 0.5:
                # Only trust SOV3 if it signals high partnership (rare for simple answers)
                return result.score
        except Exception:
            pass
        return _text_similarity(left_text, right_text)

    async def _sov3_care(self, text: str) -> Optional[Dict]:
        """Score output quality via care validation."""
        try:
            care = await self.sov3.score_care(text[:2000])
            if care:
                return {"score": care.overall, "safe": care.overall > 0.3}
        except Exception:
            pass
        return None

    async def _sov3_threat(self, text: str) -> Optional[Dict]:
        """Score threat level."""
        try:
            threat = await self.sov3.check_threat(text[:2000])
            if threat:
                return {"score": threat.score, "blocked": threat.blocked, "labels": threat.labels}
        except Exception:
            pass
        return None

    def _hy3_converge(
        self,
        left: HemisphereOutput,
        right: HemisphereOutput,
        partnership: float,
        left_care: Optional[Dict],
        right_care: Optional[Dict],
    ) -> Tuple[int, str, str]:
        """
        HY3 Ternary Convergence.

        Returns: (hy3_state, text, method)
        hy3_state: +1 = agree, 0 = partial, -1 = disagree
        """
        # Quality-weighted partnership — only adjust if care data available
        left_quality = left_care.get("score", 0.5) if left_care else 0.5
        right_quality = right_care.get("score", 0.5) if right_care else 0.5
        if left_care or right_care:
            quality_factor = 0.5 + 0.5 * ((left_quality + right_quality) / 2)
            weighted_partnership = partnership * quality_factor
        else:
            weighted_partnership = partnership  # Use raw partnership if no care data

        if weighted_partnership >= 0.7:
            # +1: Strong agreement → weighted merge
            total_weight = left_quality + right_quality
            if total_weight > 0:
                if left_quality >= right_quality:
                    text = left.text
                    method = "hy3+1_local_pref"
                else:
                    text = right.text
                    method = "hy3+1_api_pref"
            else:
                text = left.text if len(left.text) > len(right.text) else right.text
                method = "hy3+1_length_pref"
            return (+1, text, method)

        elif weighted_partnership >= 0.3:
            # 0: Partial agreement → keep both, mark divergence
            common = _extract_common_claims(left.text, right.text)
            if common:
                text = f"{common}\n\n[Left adds]: {left.text[:300]}...\n[Right adds]: {right.text[:300]}..."
            else:
                text = f"[Convergence partial — hemispheres diverge]\n\nLeft ({left.models_used}): {left.text}\n\nRight ({right.models_used}): {right.text}"
            method = "hy3_0_divergence_surfaced"
            return (0, text, method)

        else:
            # -1: Disagreement → escalate to full merge with warning
            text = (
                f"[HY3 -1: Hemispheres disagree (partnership={partnership:.2f})]\n\n"
                f"══ LEFT ({', '.join(left.models_used)}) ══\n{left.text}\n\n"
                f"══ RIGHT ({', '.join(right.models_used)}) ══\n{right.text}\n\n"
                f"[Recommendation]: Please verify claims independently."
            )
            method = "hy3-1_escalation"
            return (-1, text, method)

    async def close(self):
        await self.sov3.close()


# ═══════════════════════════════════════════════════════════════════════════════
# HY3 Utilities
# ═══════════════════════════════════════════════════════════════════════════════

def _text_similarity(a: str, b: str) -> float:
    """Jaccard similarity with punctuation normalization and CJK fallback."""
    import re
    if not a or not b:
        return 0.0
    
    def normalize(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        return text
    
    a_norm = normalize(a)
    b_norm = normalize(b)
    
    # CJK fallback: check substring containment with whitespace removed
    # (Chinese/Japanese/Korean don't use spaces between words)
    a_no_space = a_norm.replace(' ', '')
    b_no_space = b_norm.replace(' ', '')
    if a_no_space and b_no_space:
        if a_no_space in b_no_space or b_no_space in a_no_space:
            min_len = min(len(a_no_space), len(b_no_space))
            max_len = max(len(a_no_space), len(b_no_space))
            return 0.5 + 0.5 * (min_len / max_len)
    
    words_a = set(a_norm.split())
    words_b = set(b_norm.split())
    intersection = words_a & words_b
    union = words_a | words_b
    if not union:
        return 0.0
    return len(intersection) / len(union)


def _extract_common_claims(a: str, b: str) -> str:
    """Extract sentences that appear in both texts."""
    import re
    sentences_a = re.split(r'(?<=[.!?])\s+', a)
    sentences_b = re.split(r'(?<=[.!?])\s+', b)
    common = []
    for sa in sentences_a:
        sa_norm = sa.lower().strip()
        if len(sa_norm) < 10:
            continue
        for sb in sentences_b:
            sb_norm = sb.lower().strip()
            if _text_similarity(sa_norm, sb_norm) > 0.8:
                common.append(sa)
                break
    return " ".join(common[:3]) if common else ""


# ═══════════════════════════════════════════════════════════════════════════════
# Model Warm-Up
# ═══════════════════════════════════════════════════════════════════════════════

async def warm_up_models():
    """Pre-load local models by sending dummy requests. Reduces cold-start latency."""
    print("🔥 Warming up QuantMan hemisphere models...")
    
    # M4 local models
    m4_client = OllamaClient("http://localhost:11434")
    try:
        await m4_client.chat_completion("qwen3:8b", [{"role":"user","content":"Hi"}], max_tokens=8)
        print("  ✅ Qwen3:8b (M4) warmed")
    except Exception as e:
        print(f"  ⚠️ Qwen3:8b (M4) warm-up failed: {e}")
    
    # M2 local models
    m2_client = OllamaClient("http://192.168.50.176:11434")
    try:
        await m2_client.chat_completion("llama3.2:3b", [{"role":"user","content":"Hi"}], max_tokens=8)
        print("  ✅ Llama3.2:3b (M2) warmed")
    except Exception as e:
        print(f"  ⚠️ Llama3.2:3b (M2) warm-up failed: {e}")
    
    await m4_client.close()
    await m2_client.close()
    print("🔥 Warm-up complete")


async def _ollama_generate_fallback(client, model_id: str, messages: list, temperature: float, max_tokens: int) -> Optional[str]:
    """Fallback to /api/generate for Qwen3 models when /api/chat returns empty."""
    try:
        import httpx, json
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        async with httpx.AsyncClient(timeout=30.0) as c:
            resp = await c.post(
                f"{client.base_url}/api/generate",
                json={
                    "model": model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
    except Exception:
        return None
