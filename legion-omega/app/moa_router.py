#!/usr/bin/env python3
"""
Mixture of Agents (MoA) router for Legion cluster.
Queries multiple Ollama nodes in parallel, aggregates responses.
Based on: https://arxiv.org/abs/2406.04692 (Together AI MoA paper)
"""

import asyncio
import json
import urllib.request
from typing import Dict, List, Optional

# Node → character mapping — 6 GPU Legion, 3 model families
EXPERTS = {
    "hephaestus": {
        "host": "50.217.254.165", "port": 40408,
        "model": "qwen3.5:35b",
        "role": "code and implementation expert",
    },
    "argus": {
        "host": "50.217.254.173", "port": 41021,
        "model": "qwen3.5:35b",
        "role": "critical review and safety evaluation expert",
    },
    "valkyrie": {
        # RTX PRO 4500 — gemma3:12b (Google family)
        "host": "165.166.241.251", "port": 50938,
        "model": "gemma3:12b",
        "role": "Google Gemma multimodal reasoning and synthesis expert",
    },
    "prometheus": {
        # RTX 5090 108 TFLOPS — deepseek-r1:7b (chain-of-thought family)
        "host": "142.171.48.138", "port": 33224,
        "model": "deepseek-r1:7b",
        "role": "deep chain-of-thought reasoning and step-by-step analysis expert",
    },
    "titan": {
        # RTX 4080S — qwen3.5:9b (fast synthesis)
        "host": "175.155.64.174", "port": 19925,
        "model": "qwen3.5:9b",
        "role": "fast synthesis and concise summarization expert",
    },
}

# RTX 5090 aggregator — 108 TFLOPS, fastest node
AGGREGATOR_5090 = {"host": "142.171.48.138", "port": 33224, "model": "qwen3.5:9b"}

AGGREGATOR = EXPERTS["odyssey"]  # Local M4 runs synthesis


def _ollama_generate(host: str, port: int, model: str, prompt: str, timeout: int = 120) -> str:
    """Synchronous Ollama call."""
    url = f"http://{host}:{port}/api/generate"
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())["response"]
    except Exception as e:
        return f"[ERROR: {e}]"


async def _async_query(expert_id: str, cfg: dict, prompt: str) -> tuple[str, str]:
    """Run a single expert query in a thread pool."""
    loop = asyncio.get_event_loop()
    system_prompt = f"You are a {cfg['role']}. Provide your expert perspective concisely.\n\n{prompt}"
    response = await loop.run_in_executor(
        None,
        _ollama_generate,
        cfg["host"], cfg["port"], cfg["model"], system_prompt,
    )
    return expert_id, response


async def query_all_experts(
    prompt: str,
    experts: Optional[Dict] = None,
    timeout_per_expert: int = 90,
) -> Dict[str, str]:
    """Query all experts in parallel. Returns {expert_id: response}."""
    targets = experts or EXPERTS
    tasks = [_async_query(eid, cfg, prompt) for eid, cfg in targets.items()]

    results = {}
    done = await asyncio.gather(*tasks, return_exceptions=True)
    for item in done:
        if isinstance(item, Exception):
            continue
        eid, response = item
        results[eid] = response

    return results


def aggregate(expert_responses: Dict[str, str], original_prompt: str) -> str:
    """Synthesise multiple expert responses into one final answer."""
    if not expert_responses:
        return "[No expert responses available]"

    parts = []
    for eid, resp in expert_responses.items():
        cfg = EXPERTS.get(eid, {})
        role = cfg.get("role", eid)
        parts.append(f"--- {eid.upper()} ({role}) ---\n{resp}")

    synthesis_prompt = (
        f"You have received responses from {len(parts)} expert AI systems on this question:\n\n"
        f"QUESTION: {original_prompt}\n\n"
        + "\n\n".join(parts)
        + "\n\nSynthesize these into ONE definitive, comprehensive answer. "
        "Use the best insights from each expert. Be concise but complete."
    )

    return _ollama_generate(
        AGGREGATOR["host"],
        AGGREGATOR["port"],
        AGGREGATOR["model"],
        synthesis_prompt,
    )


async def run(prompt: str, verbose: bool = True) -> str:
    """Full MoA pipeline: parallel queries → aggregation."""
    if verbose:
        print(f"[MoA] Querying {len(EXPERTS)} experts in parallel...")

    responses = await query_all_experts(prompt)

    if verbose:
        for eid, resp in responses.items():
            print(f"  [{eid}] {resp[:120]}...")

    print(f"[MoA] Aggregating {len(responses)} responses...")
    final = aggregate(responses, prompt)
    return final


if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is the most important thing to optimize in a GPU inference cluster?"
    result = asyncio.run(run(prompt))
    print("\n=== FINAL ANSWER ===")
    print(result)
