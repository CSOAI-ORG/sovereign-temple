#!/usr/bin/env python3
"""
SWEET SPOT BENCHMARK — Find the optimal model routing configuration.
Tests all available endpoints with real tasks, measures actual latency & throughput.
"""
import asyncio
import time
import json
import sys
sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, "/Users/nicholas/clawd/sovereign-temple")
from openrouter_client import get_client


# Test tasks representative of actual usage
TASKS = [
    ("greeting", "LEFT", "Hello, how are you today?"),
    ("coding", "LEFT", "Write a Python function to parse JSON recursively. Include error handling."),
    ("debug", "LEFT", "Debug this error: TypeError in React map function."),
    ("creative", "RIGHT", "Write a haiku about passive drainage in Lincolnshire clay."),
    ("reasoning", "RIGHT", "Why is thermal mass more effective than insulation alone in passive solar?"),
]

# Endpoints to test — prioritized by likelihood of success
ENDPOINTS = [
    ("local_gemma4", "ollama", "http://localhost:11434", "gemma4:e4b", 128),
    ("vast_llama31", "ollama", "http://localhost:11436", "llama3.1:8b", 128),
    ("vast_llama32", "ollama", "http://localhost:11436", "llama3.2:3b", 128),
    ("openrouter_deepseek_flash", "openrouter", None, "deepseek/deepseek-v4-flash:free", 256),
    ("openrouter_gemma4_31b", "openrouter", None, "google/gemma-4-31b-it:free", 256),
]


async def test_ollama(base_url, model_id, task_text, max_tokens, timeout=20):
    import aiohttp
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": task_text}],
        "stream": False,
        "options": {"num_predict": max_tokens, "temperature": 0.7},
    }
    start = time.perf_counter()
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
        async with session.post(f"{base_url}/api/chat", json=payload) as resp:
            data = await resp.json()
    latency_ms = (time.perf_counter() - start) * 1000
    text = data.get("message", {}).get("content", "")
    tokens_out = len(text.split())
    return {
        "text": text,
        "latency_ms": latency_ms,
        "tokens_out": tokens_out,
        "tokens_per_sec": tokens_out / (latency_ms / 1000) if latency_ms > 0 else 0,
        "cost_usd": 0.0,
        "success": bool(text),
    }


async def test_openrouter(client, model_id, task_text, max_tokens, timeout=60):
    messages = [{"role": "user", "content": task_text}]
    start = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            client.chat_completion(
                model_id=model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            ),
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "text": result.text,
            "latency_ms": latency_ms,
            "tokens_out": result.tokens_out,
            "tokens_per_sec": result.tokens_out / (latency_ms / 1000) if latency_ms > 0 else 0,
            "cost_usd": result.cost_usd,
            "success": True,
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000
        return {
            "text": "", "latency_ms": latency_ms, "tokens_out": 0,
            "tokens_per_sec": 0, "cost_usd": 0.0, "success": False, "error": str(exc)[:80],
        }


async def run():
    client = get_client()
    results = []

    print("=" * 70)
    print("SWEET SPOT BENCHMARK")
    print("=" * 70)

    for endpoint_name, provider, base_url, model_id, max_tokens in ENDPOINTS:
        print(f"\n🔬 {endpoint_name} ({model_id})")
        for task_type, expected_hemi, task_text in TASKS:
            print(f"   → {task_type}...", end=" ", flush=True)
            try:
                if provider == "ollama":
                    raw = await test_ollama(base_url, model_id, task_text, max_tokens)
                else:
                    raw = await test_openrouter(client, model_id, task_text, max_tokens)

                r = {
                    "endpoint": endpoint_name,
                    "model_id": model_id,
                    "task_type": task_type,
                    "latency_ms": round(raw["latency_ms"], 1),
                    "tokens_out": raw["tokens_out"],
                    "tokens_per_sec": round(raw["tokens_per_sec"], 1),
                    "cost_usd": raw["cost_usd"],
                    "success": raw["success"],
                    "error": raw.get("error", ""),
                    "snippet": raw["text"][:80].replace("\n", " "),
                }
                status = "✅"
                detail = f"{r['latency_ms']}ms | {r['tokens_out']}tok | {r['tokens_per_sec']}tok/s"
            except Exception as exc:
                r = {
                    "endpoint": endpoint_name, "model_id": model_id,
                    "task_type": task_type, "latency_ms": 0, "tokens_out": 0,
                    "tokens_per_sec": 0, "cost_usd": 0, "success": False,
                    "error": str(exc)[:80], "snippet": "",
                }
                status = "❌"
                detail = str(exc)[:60]
            results.append(r)
            print(f"{status} {detail}")
            await asyncio.sleep(0.3)

    await client.close()

    # Analysis
    print("\n" + "=" * 70)
    print("SWEET SPOT ANALYSIS")
    print("=" * 70)

    by_task = {}
    for r in results:
        by_task.setdefault(r["task_type"], []).append(r)

    recommendations = {}
    for task_type, task_results in by_task.items():
        successful = [r for r in task_results if r["success"]]
        if not successful:
            continue
        fastest = min(successful, key=lambda x: x["latency_ms"])
        best_tps = max(successful, key=lambda x: x["tokens_per_sec"])
        recommendations[task_type] = {
            "fastest": fastest["endpoint"],
            "best_tps": best_tps["endpoint"],
        }
        print(f"\n📊 {task_type.upper()}")
        print(f"   Fastest:  {fastest['endpoint']} ({fastest['latency_ms']}ms)")
        print(f"   Best tps: {best_tps['endpoint']} ({best_tps['tokens_per_sec']} tok/s)")

    print("\n" + "-" * 70)
    print("ENDPOINT AVG LATENCY (successful only)")
    print("-" * 70)
    by_endpoint = {}
    for r in results:
        if r["success"]:
            by_endpoint.setdefault(r["endpoint"], []).append(r["latency_ms"])
    for ep, latencies in sorted(by_endpoint.items(), key=lambda x: sum(x[1]) / len(x[1])):
        avg = sum(latencies) / len(latencies)
        print(f"  {ep:30s} avg={avg:>7.1f}ms  n={len(latencies)}")

    with open("/tmp/benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n💾 Saved to /tmp/benchmark_results.json")
    return results


if __name__ == "__main__":
    asyncio.run(run())
