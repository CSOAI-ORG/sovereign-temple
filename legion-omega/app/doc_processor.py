#!/usr/bin/env python3
"""
Legion document processor — runs 1010+ documents across all GPU nodes.
Uses MoA (Mixture of Agents) to process each document in parallel.

Usage:
    python3 app/doc_processor.py --input /path/to/docs/ --output /path/to/results/
    python3 app/doc_processor.py --demo  # Run with synthetic docs
"""

import asyncio
import json
import os
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import urllib.request

# Node registry — updated dynamically
NODES = {
    "hephaestus": {"host": "50.217.254.165", "port": 40408, "model": "qwen3.5:35b"},   # RTX 8000
    "argus":      {"host": "50.217.254.173", "port": 41021, "model": "qwen3.5:35b"},   # RTX 8000
    "valkyrie":   {"host": "165.166.241.251", "port": 50938, "model": "gemma3:12b"},    # RTX PRO 4500 — Google Gemma
    "prometheus": {"host": "142.171.48.138",  "port": 33224, "model": "deepseek-r1:7b"},# RTX 5090 — DeepSeek R1
}


def _ollama_query(host: str, port: int, model: str, prompt: str, timeout: int = 180) -> str:
    url = f"http://{host}:{port}/api/generate"
    # think:false disables chain-of-thought on thinking models (e.g. qwen3.5:9b)
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "think": False}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()).get("response", "")
    except Exception as e:
        return f"[ERROR: {e}]"


async def process_document(
    doc_id: int,
    text: str,
    task: str,
    node_id: str,
) -> Dict:
    """Process a single document on a specific node."""
    cfg = NODES.get(node_id)
    if not cfg:
        return {"doc_id": doc_id, "node": node_id, "error": "unknown node"}

    prompt = f"""Document #{doc_id}:

{text[:8000]}

Task: {task}

Provide a concise, structured response."""

    loop = asyncio.get_event_loop()
    t0 = time.time()
    response = await loop.run_in_executor(
        None, _ollama_query,
        cfg["host"], cfg["port"], cfg["model"], prompt
    )
    elapsed = time.time() - t0

    return {
        "doc_id": doc_id,
        "node": node_id,
        "model": cfg["model"],
        "elapsed_s": round(elapsed, 1),
        "response": response,
        "tokens_est": len(response) // 4,
    }


async def process_batch(
    docs: List[Dict],
    task: str,
    results_dir: Path,
    concurrency: int = 6,
) -> List[Dict]:
    """Process all documents, distributing round-robin across nodes."""
    node_ids = list(NODES.keys())
    results = []
    sem = asyncio.Semaphore(concurrency)

    async def run_one(i: int, doc: Dict):
        node = node_ids[i % len(node_ids)]
        async with sem:
            result = await process_document(
                doc_id=doc.get("id", i),
                text=doc.get("text", ""),
                task=task,
                node_id=node,
            )
            # Save incrementally
            out_path = results_dir / f"doc_{result['doc_id']:05d}.json"
            out_path.write_text(json.dumps(result, indent=2))

            status = "✅" if not result.get("error") else "❌"
            print(f"  {status} [{result['node']:12}] doc {result['doc_id']:4d}  {result['elapsed_s']}s  ~{result.get('tokens_est', 0)} tokens")
            return result

    tasks = [run_one(i, doc) for i, doc in enumerate(docs)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]


def load_documents(path: str) -> List[Dict]:
    """Load documents from a directory or file."""
    p = Path(path)
    docs = []
    if p.is_dir():
        for i, f in enumerate(sorted(p.glob("**/*.txt")) + sorted(p.glob("**/*.md"))):
            docs.append({"id": i, "path": str(f), "text": f.read_text(errors="ignore")})
        for i, f in enumerate(sorted(p.glob("**/*.json")), start=len(docs)):
            try:
                data = json.loads(f.read_text())
                if isinstance(data, list):
                    for j, item in enumerate(data):
                        docs.append({"id": len(docs) + j, "text": str(item)})
                else:
                    docs.append({"id": len(docs), "text": str(data)})
            except Exception:
                pass
    elif p.suffix == ".json":
        data = json.loads(p.read_text())
        if isinstance(data, list):
            for i, item in enumerate(data):
                docs.append({"id": i, "text": str(item)})
    return docs


def generate_synthetic_docs(count: int = 100) -> List[Dict]:
    """Generate synthetic test documents."""
    topics = [
        "AI safety and alignment", "GPU cluster optimization", "Distributed inference",
        "Character-based AI systems", "Autonomous agent design", "Multi-node orchestration",
        "Regulatory compliance for AI", "Neural architecture search", "Token efficiency",
        "Federated learning", "Model quantization", "Context window management",
    ]
    docs = []
    for i in range(count):
        topic = topics[i % len(topics)]
        docs.append({
            "id": i,
            "text": f"""Topic: {topic}
Document {i+1} of {count}

This document discusses {topic} in the context of the Legion AI cluster.
Key considerations include performance, reliability, cost efficiency, and safety.
The cluster consists of multiple GPU nodes (RTX 8000, A6000, RTX 4080S) coordinated
via Ollama. Each node runs specialized models for different task types.

Questions to analyze:
1. How does {topic} apply to distributed GPU inference?
2. What are the tradeoffs at the node level?
3. Recommend three concrete improvements.
""",
        })
    return docs


def print_summary(results: List[Dict], elapsed_total: float):
    succeeded = [r for r in results if not r.get("error")]
    failed = [r for r in results if r.get("error")]
    total_tokens = sum(r.get("tokens_est", 0) for r in succeeded)
    avg_time = sum(r.get("elapsed_s", 0) for r in succeeded) / max(len(succeeded), 1)

    print("\n" + "="*60)
    print(f"DOCUMENT PROCESSING COMPLETE")
    print("="*60)
    print(f"  Processed   : {len(succeeded):,} documents")
    print(f"  Failed      : {len(failed)}")
    print(f"  Total time  : {elapsed_total:.1f}s ({elapsed_total/60:.1f}min)")
    print(f"  Avg per doc : {avg_time:.1f}s")
    print(f"  Total tokens: ~{total_tokens:,}")
    print(f"  Throughput  : {len(succeeded)/elapsed_total:.2f} docs/sec")
    print("="*60)

    # Node breakdown
    by_node: Dict[str, List] = {}
    for r in succeeded:
        by_node.setdefault(r["node"], []).append(r)
    print("\nNode breakdown:")
    for node, node_results in sorted(by_node.items()):
        avg = sum(r["elapsed_s"] for r in node_results) / len(node_results)
        print(f"  {node:14} {len(node_results):4d} docs  avg {avg:.1f}s/doc")


async def main(args):
    results_dir = Path(args.output)
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"🐉 LEGION DOCUMENT PROCESSOR")
    print(f"   Nodes: {', '.join(NODES.keys())}")
    print(f"   Task : {args.task}")
    print(f"   Out  : {results_dir}\n")

    # Load documents
    if args.demo:
        count = args.count or 20
        print(f"Generating {count} synthetic documents...")
        docs = generate_synthetic_docs(count)
    elif args.input:
        print(f"Loading documents from {args.input}...")
        docs = load_documents(args.input)
        if args.count:
            docs = docs[:args.count]
    else:
        print("Error: specify --input or --demo")
        sys.exit(1)

    print(f"Processing {len(docs)} documents across {len(NODES)} nodes...\n")
    t0 = time.time()

    results = await process_batch(docs, args.task, results_dir, concurrency=args.concurrency)

    elapsed = time.time() - t0
    print_summary(results, elapsed)

    # Write combined results
    combined = results_dir / "results_combined.json"
    combined.write_text(json.dumps(results, indent=2))
    print(f"\nFull results → {combined}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Legion document processor")
    parser.add_argument("--input", help="Input directory or JSON file")
    parser.add_argument("--output", default="/tmp/legion_results", help="Output directory")
    parser.add_argument("--task", default="Analyze this document: summarize key points, identify main themes, and suggest 3 actionable insights.", help="Processing task")
    parser.add_argument("--count", type=int, help="Max documents to process")
    parser.add_argument("--concurrency", type=int, default=3, help="Parallel requests (default 3)")
    parser.add_argument("--demo", action="store_true", help="Run with synthetic docs")
    args = parser.parse_args()

    asyncio.run(main(args))
