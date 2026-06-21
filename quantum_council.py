#!/usr/bin/env python3
"""
Quantum Council - Multi-LLM Parallel Execution
Runs multiple LLMs simultaneously and synthesizes responses
"""

import asyncio
import json
import time
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import queue
import threading


@dataclass
class CouncilMember:
    name: str
    model: str
    endpoint: str
    strengths: List[str] = None
    enabled: bool = True

    def __post_init__(self):
        if self.strengths is None:
            self.strengths = []


class QuantumCouncil:
    """
    Parallel multi-LLM execution with result synthesis
    All models run simultaneously, responses synthesized
    """

    def __init__(self):
        self.members: List[CouncilMember] = []
        self._setup_council()

    def _setup_council(self):
        """Initialize council members"""

        # Primary: Gemma 4 on Vast.ai
        self.members.append(
            CouncilMember(
                name="Gemma 4",
                model="gemma4:31b",
                endpoint="http://localhost:11436/api/chat",
                strengths=["reasoning", "vision", "multimodal", "speed"],
            )
        )

        # Local Ollama (check what's available)
        self.members.append(
            CouncilMember(
                name="Qwen Local",
                model="qwen2.5:7b",
                endpoint="http://localhost:11434/api/chat",
                strengths=["fast", "conversational"],
            )
        )

        # Cloud fallback via OpenRouter (if API key available)
        import os

        if os.getenv("OPENROUTER_API_KEY"):
            self.members.append(
                CouncilMember(
                    name="DeepSeek R1",
                    model="deepseek/deepseek-r1",
                    endpoint="https://openrouter.ai/api/v1/chat/completions",
                    strengths=["reasoning", "analysis"],
                )
            )

    async def query(self, prompt: str, num_members: int = None) -> Dict[str, Any]:
        """
        Query all council members in parallel
        Returns: {responses: [...], consensus: str, timing: ms}
        """
        start = time.time()

        # Filter enabled members
        active = [m for m in self.members if m.enabled]
        if num_members:
            active = active[:num_members]

        print(f"🔮 Quantum Council: {len(active)} members responding...")

        # Run all in parallel
        tasks = [self._query_member(m, prompt) for m in active]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful responses
        responses = []
        for member, result in zip(active, results):
            if isinstance(result, Exception):
                print(f"  ⚠️ {member.name}: {result}")
            else:
                responses.append(
                    {
                        "member": member.name,
                        "model": member.model,
                        "response": result,
                        "strengths": member.strengths,
                    }
                )
                print(f"  ✅ {member.name}: {len(result)} chars")

        # Synthesize
        synthesis = self._synthesize(responses, prompt)

        elapsed = (time.time() - start) * 1000

        return {
            "responses": responses,
            "synthesis": synthesis,
            "members_responded": len(responses),
            "total_members": len(active),
            "timing_ms": elapsed,
        }

    async def _query_member(self, member: CouncilMember, prompt: str) -> str:
        """Query a single council member"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Determine request format based on endpoint
            if "openrouter" in member.endpoint:
                import os

                res = await client.post(
                    member.endpoint,
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
                    },
                    json={
                        "model": member.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1024,
                        "temperature": 0.7,
                    },
                )
                data = res.json()
                return (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
            else:
                # Ollama format
                res = await client.post(
                    member.endpoint,
                    json={
                        "model": member.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"num_predict": 1024, "temperature": 0.7},
                    },
                )
                data = res.json()
                return data.get("message", {}).get("content", "") or data.get(
                    "thinking", ""
                )

    def _synthesize(self, responses: List[Dict], original_prompt: str) -> str:
        """Synthesize multiple responses into one coherent answer"""
        if not responses:
            return "No responses from council members."

        if len(responses) == 1:
            return responses[0]["response"]

        # Simple synthesis - concatenate with attribution
        parts = []
        for r in responses:
            parts.append(f"[{r['member']}]: {r['response'][:300]}")

        return "\n\n".join(parts)

    def get_status(self) -> Dict:
        """Get council status"""
        return {
            "members": [
                {
                    "name": m.name,
                    "model": m.model,
                    "enabled": m.enabled,
                    "strengths": m.strengths,
                }
                for m in self.members
            ]
        }


# Global council
_council: Optional[QuantumCouncil] = None


def get_council() -> QuantumCouncil:
    global _council
    if _council is None:
        _council = QuantumCouncil()
    return _council


if __name__ == "__main__":

    async def test():
        council = get_council()
        print("=== Quantum Council Status ===")
        print(json.dumps(council.get_status(), indent=2))

        print("\n=== Testing Council ===")
        result = await council.query(
            "What is the meaning of life? Give me a short answer."
        )
        print(f"\nSynthesis: {result['synthesis'][:500]}...")
        print(
            f"\nTiming: {result['timing_ms']:.0f}ms, {result['members_responded']}/{result['total_members']} responded"
        )

    asyncio.run(test())
