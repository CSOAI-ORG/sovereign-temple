#!/usr/bin/env python3
"""Benchmark paid OpenRouter models + Vast.ai GPU."""
import asyncio, sys, time, json
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, "/Users/nicholas/clawd/sovereign-temple")
from openrouter_client import get_client
from ollama_client import get_vast_ollama

TASKS = [
    ("greeting", "Hello, how are you today?"),
    ("coding", "Write a Python function to parse JSON recursively."),
    ("debug", "Debug this React error: TypeError Cannot read property map of undefined."),
    ("creative", "Write a haiku about drainage in clay soil."),
    ("reasoning", "Why is thermal mass more effective than insulation in passive solar design?"),
]

MODELS = [
    ("deepseek-v4-flash", "deepseek/deepseek-v4-flash", "openrouter"),
    ("deepseek-v4-pro", "deepseek/deepseek-v4-pro", "openrouter"),
    ("kimi-k2.6", "moonshotai/kimi-k2.6", "openrouter"),
    ("llama3.1-vast", "llama3.1:8b", "ollama"),
]

async def run():
    or_client = get_client()
    ollama_client = get_vast_ollama()
    results = []

    print("=" * 75)
    print("PAID MODEL BENCHMARK — $25 Unlocked")
    print("=" * 75)

    for name, model_id, provider in MODELS:
        print(f"\n🔬 {name} ({model_id})")
        for task_type, task_text in TASKS:
            print(f"   → {task_type}...", end=" ", flush=True)
            start = time.perf_counter()
            try:
                if provider == "openrouter":
                    r = await or_client.chat_completion(
                        model_id=model_id,
                        messages=[{"role": "user", "content": task_text}],
                        max_tokens=256,
                        temperature=0.7,
                    )
                    latency = r.latency_ms
                    text = r.text
                    tokens_out = r.tokens_out
                    cost = r.cost_usd
                else:
                    r = await ollama_client.chat_completion(
                        model_id=model_id,
                        messages=[{"role": "user", "content": task_text}],
                        max_tokens=256,
                        temperature=0.7,
                    )
                    latency = r.latency_ms
                    text = r.text
                    tokens_out = r.tokens_out
                    cost = 0.0

                tps = tokens_out / (latency / 1000) if latency > 0 else 0
                results.append({
                    "model": name, "task": task_type, "latency_ms": latency,
                    "tokens_out": tokens_out, "tps": round(tps, 1),
                    "cost_usd": cost, "success": bool(text),
                    "snippet": text[:60].replace("\n", " "),
                })
                print(f"✅ {latency:>7.1f}ms | {tokens_out:>3}tok | ${cost:.6f} | {text[:40]}")
            except Exception as exc:
                latency = (time.perf_counter() - start) * 1000
                results.append({
                    "model": name, "task": task_type, "latency_ms": latency,
                    "tokens_out": 0, "tps": 0, "cost_usd": 0, "success": False,
                    "error": str(exc)[:60],
                })
                print(f"❌ {str(exc)[:50]}")
            await asyncio.sleep(0.5)

    await or_client.close()

    # Analysis
    print("\n" + "=" * 75)
    print("SWEET SPOT — PAID TIER")
    print("=" * 75)

    by_task = {}
    for r in results:
        by_task.setdefault(r["task"], []).append(r)

    for task, rs in by_task.items():
        ok = [x for x in rs if x["success"]]
        if not ok:
            continue
        fastest = min(ok, key=lambda x: x["latency_ms"])
        cheapest = min(ok, key=lambda x: x["cost_usd"])
        best_tps = max(ok, key=lambda x: x["tps"])
        print(f"\n📊 {task.upper()}")
        print(f"   Fastest:  {fastest['model']:20s} {fastest['latency_ms']:>7.1f}ms")
        print(f"   Cheapest: {cheapest['model']:20s} ${cheapest['cost_usd']:.6f}")
        print(f"   Best tps: {best_tps['model']:20s} {best_tps['tps']:>5.1f} tok/s")

    print("\n" + "-" * 75)
    print("MODEL AVERAGES (successful only)")
    print("-" * 75)
    by_model = {}
    for r in results:
        if r["success"]:
            by_model.setdefault(r["model"], []).append(r["latency_ms"])
    for m, lats in sorted(by_model.items(), key=lambda x: sum(x[1])/len(x[1])):
        avg = sum(lats) / len(lats)
        print(f"  {m:20s} avg={avg:>7.1f}ms  n={len(lats)}")

    with open("/tmp/benchmark_paid.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n💾 Saved to /tmp/benchmark_paid.json")

asyncio.run(run())
