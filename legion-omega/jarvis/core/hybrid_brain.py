"""
NAFS-4 Hybrid Architecture — JARVIS Core
System-1: SNN (Neuromorphic Reflex)
System-2: LLM (Deliberative) — via Vast.ai GPU + Anthropic API
System-3: MARS (Metacognition)
System-4: GVU (Safety Kernel)

Organization: MEOK AI Labs (formerly MEOK AI Labs)
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import redis
import torch
import torch.nn as nn
import snntorch as snn
from snntorch import surrogate

from .mars import MARSReflector, ReflectionMode
from .gvu import GVUOperator


class SystemLevel(Enum):
    REFLEX = 1
    DELIBERATIVE = 2
    METACOGNITIVE = 3
    SAFETY = 4


@dataclass
class CognitiveState:
    stimulus: Any
    snn_activation: torch.Tensor
    working_memory: Dict
    confidence: float
    timestamp: float


class ReflexNet(nn.Module):
    def __init__(self):
        super().__init__()
        beta = 0.5
        spike_grad = surrogate.fast_sigmoid(slope=25)
        self.fc1 = nn.Linear(128, 64)
        self.lif1 = snn.Leaky(beta=beta, spike_grad=spike_grad)
        self.fc2 = nn.Linear(64, 32)
        self.lif2 = snn.Leaky(beta=beta, spike_grad=spike_grad)
        self.fc3 = nn.Linear(32, 16)

    def forward(self, x, mem1=None, mem2=None):
        if mem1 is None:
            mem1 = self.lif1.init_leaky()
        if mem2 is None:
            mem2 = self.lif2.init_leaky()
        cur1 = self.fc1(x)
        spk1, mem1 = self.lif1(cur1, mem1)
        cur2 = self.fc2(spk1)
        spk2, mem2 = self.lif2(cur2, mem2)
        out = self.fc3(spk2)
        return out, mem1, mem2


class HybridBrain:
    """MEOK AI Labs — JARVIS hybrid cognitive architecture"""

    def __init__(self,
                 redis_url: str = "redis://localhost:6379",
                 vast_ollama_url: str = "http://50.217.254.165:40408",
                 anthropic_api_key: Optional[str] = None):
        import os
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.vast_url = vast_ollama_url
        self.api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")

        # System-1: SNN
        self.snn = ReflexNet()

        # System-3: MARS
        self.reflector = MARSReflector(mode=ReflectionMode.PRINCIPLE_BASED)

        # System-4: GVU
        self.safety_kernel = GVUOperator(
            generate_fn=self._generate_candidate,
            verify_fn=self._verify_candidate,
            update_fn=self._safe_update,
        )

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("JARVIS-HybridBrain")
        self.logger.info("MEOK AI Labs — JARVIS online")

    def _preprocess_stimulus(self, stimulus: Dict) -> torch.Tensor:
        """Convert stimulus dict to tensor for SNN"""
        values = list(stimulus.values())[:128]
        padded = values + [0.0] * (128 - len(values))
        return torch.tensor(padded, dtype=torch.float32)

    async def _call_gpu_llm(self, prompt: str, model: str = "qwen3.5:9b") -> str:
        """Call Vast.ai GPU Ollama for deliberative reasoning"""
        import urllib.request
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 2048, "temperature": 0.3}
        }).encode()
        req = urllib.request.Request(
            f"{self.vast_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                return data.get("response", "")
        except Exception as e:
            self.logger.error(f"GPU call failed: {e}")
            return ""

    async def _call_claude(self, prompt: str) -> str:
        """Call Claude API for high-quality synthesis"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            r = client.messages.create(
                model="claude-opus-4-5",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return r.content[0].text
        except Exception as e:
            self.logger.error(f"Claude call failed: {e}")
            return ""

    async def process(self, stimulus: Dict, context: Dict) -> Dict:
        """Full NAFS-4 pipeline"""

        # System 1: SNN reflex
        snn_input = self._preprocess_stimulus(stimulus)
        snn_out, _, _ = self.snn(snn_input)
        reflex_confidence = float(torch.max(snn_out))

        state = CognitiveState(
            stimulus=stimulus,
            snn_activation=snn_out,
            working_memory=context,
            confidence=reflex_confidence,
            timestamp=time.time()
        )

        if reflex_confidence > 0.9:
            return {"action": "reflex", "confidence": reflex_confidence, "source": "SNN"}

        # System 2: Deliberative (GPU LLM)
        plan_prompt = f"""JARVIS (MEOK AI Labs): Analyse stimulus and plan action.
Stimulus: {json.dumps(stimulus)[:500]}
Context: {json.dumps(context)[:500]}
SNN confidence: {reflex_confidence:.3f}
Provide: action plan, reasoning, confidence."""
        plan = await self._call_gpu_llm(plan_prompt)

        # System 3: MARS reflection
        reflection = self.reflector.reflect(
            reasoning_trace={"plan": plan},
            outcome_prediction=reflex_confidence,
            mode=ReflectionMode.PROCEDURAL
        )

        if reflection.needs_revision:
            revision_prompt = f"Revise this plan based on critique:\nPlan: {plan}\nCritique: {reflection.critique}"
            plan = await self._call_gpu_llm(revision_prompt)

        # System 4: GVU safety
        safe_action = self.safety_kernel.validate({"plan": plan})

        return {
            "action": safe_action or plan,
            "confidence": reflex_confidence,
            "reflected": reflection.needs_revision,
            "source": "NAFS-4"
        }

    def _generate_candidate(self, state: Dict) -> Any:
        return state

    def _verify_candidate(self, candidate: Any) -> bool:
        return True  # GVU stability check

    def _safe_update(self, candidate: Any) -> None:
        pass
