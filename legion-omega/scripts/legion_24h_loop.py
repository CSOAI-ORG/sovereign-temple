#!/usr/bin/env python3
"""
Legion 24-hour continuous processing loop.
Runs document sprints on all 6 GPU nodes, cycling through topic batches.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add app dir to path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

DURATION_HOURS = 24
DOCS_PER_BATCH = 200
OUTPUT_BASE = Path("/tmp/legion_24h")

# Topic batches — rotate through these for diversity
TASK_BATCHES = [
    "Analyze this document: summarize key points, identify main themes, and suggest 3 actionable insights.",
    "Evaluate this document for technical accuracy, implementation feasibility, and potential risks. Provide a structured assessment.",
    "Extract all decisions, recommendations, and open questions from this document. Format as a structured report.",
    "Critique this document: identify weaknesses, gaps in reasoning, and suggest specific improvements.",
    "Summarize this document for a non-technical executive audience. Focus on business impact and strategic implications.",
    "Identify all AI safety and alignment considerations in this document. Rate risks and propose mitigations.",
    "Extract actionable engineering tasks from this document. Format as a prioritized backlog with effort estimates.",
    "Analyze the architecture and design decisions in this document. Identify tradeoffs and alternatives.",
    "Review this document for completeness. What critical information is missing? What assumptions are unstated?",
    "Generate 5 follow-up research questions this document raises. For each, describe what answering it would unlock.",
]


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def run_batch(batch_num: int, task: str, nodes: dict, concurrency: int = 12):
    """Run one batch of documents."""
    from doc_processor import generate_synthetic_docs, process_batch

    out_dir = OUTPUT_BASE / f"batch_{batch_num:04d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    docs = generate_synthetic_docs(DOCS_PER_BATCH)
    log(f"Batch {batch_num}: {DOCS_PER_BATCH} docs across {len(nodes)} nodes")
    log(f"Task: {task[:80]}...")

    # Temporarily override NODES in doc_processor
    import doc_processor
    original_nodes = doc_processor.NODES.copy()
    doc_processor.NODES.update(nodes)

    t0 = time.time()
    results = await process_batch(docs, task, out_dir, concurrency=concurrency)
    elapsed = time.time() - t0

    doc_processor.NODES = original_nodes

    ok = [r for r in results if not r.get("error") and "[ERROR" not in r.get("response", "")]
    tokens = sum(r.get("tokens_est", 0) for r in ok)
    log(f"Batch {batch_num} done: {len(ok)}/{DOCS_PER_BATCH} ok | {elapsed:.0f}s | ~{tokens:,} tokens")

    # Save combined
    (out_dir / "batch_summary.json").write_text(json.dumps({
        "batch": batch_num,
        "task": task,
        "docs": len(ok),
        "elapsed_s": round(elapsed, 1),
        "tokens_est": tokens,
        "timestamp": datetime.now().isoformat(),
    }, indent=2))

    return len(ok), tokens


async def main():
    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

    # Node config — 4 active GPU nodes, 3 model families
    # titan (4080S) excluded: outbound HTTPS blocked, can't pull models
    NODES_6GPU = {
        "hephaestus": {"host": "50.217.254.165", "port": 40408, "model": "qwen3.5:35b"},  # RTX 8000
        "argus":      {"host": "50.217.254.173", "port": 41021, "model": "qwen3.5:35b"},  # RTX 8000
        "valkyrie":   {"host": "165.166.241.251", "port": 50938, "model": "gemma3:12b"},   # RTX PRO 4500
        "prometheus": {"host": "142.171.48.138",  "port": 33224, "model": "deepseek-r1:7b"}, # RTX 5090
    }

    log("=" * 60)
    log("LEGION 24-HOUR SPRINT STARTING")
    log(f"Nodes: {', '.join(NODES_6GPU.keys())}")
    log(f"Duration: {DURATION_HOURS}h | Batch size: {DOCS_PER_BATCH} docs")
    log("=" * 60)

    start = time.time()
    deadline = start + DURATION_HOURS * 3600
    batch_num = 0
    total_docs = 0
    total_tokens = 0

    while time.time() < deadline:
        task = TASK_BATCHES[batch_num % len(TASK_BATCHES)]
        docs, tokens = await run_batch(batch_num, task, NODES_6GPU)
        total_docs += docs
        total_tokens += tokens
        batch_num += 1

        elapsed_h = (time.time() - start) / 3600
        remaining_h = (deadline - time.time()) / 3600
        log(f"Running total: {total_docs:,} docs | ~{total_tokens:,} tokens | {elapsed_h:.1f}h elapsed | {remaining_h:.1f}h left")

    elapsed_total = time.time() - start
    log("=" * 60)
    log(f"24-HOUR SPRINT COMPLETE")
    log(f"Total docs   : {total_docs:,}")
    log(f"Total tokens : ~{total_tokens:,}")
    log(f"Total batches: {batch_num}")
    log(f"Elapsed      : {elapsed_total/3600:.1f}h")
    log("=" * 60)

    (OUTPUT_BASE / "final_summary.json").write_text(json.dumps({
        "total_docs": total_docs,
        "total_tokens": total_tokens,
        "batches": batch_num,
        "elapsed_hours": round(elapsed_total / 3600, 2),
        "completed_at": datetime.now().isoformat(),
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
