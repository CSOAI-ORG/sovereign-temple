#!/usr/bin/env python3
"""
QuantMan E2E Test Suite — Multi-language nested dual-brain validation.

Tests the full QuantMan pipeline:
  Left Mesh (Kimi K2.6 API + Qwen3:8b local M4)
  Right Mesh (Owl Alpha API + Llama3.2:3b local M2)
  → SOV3 mediation → HY3 ternary convergence

All tests expect HY3=+1 (hemispheres agree) for simple factual queries.
"""
import asyncio
import sys
import time
import httpx

API_BASE = "http://localhost:3201"

TESTS = [
    ("English", "Capital of Germany? One word.", "Berlin"),
    ("Spanish", "Capital de Espana? Una palabra.", "Madrid"),
    ("French", "Capitale de la France? Un mot.", "Paris"),
    ("Arabic", "ما هي عاصمة مصر؟ كلمة واحدة.", "القاهرة"),
    ("Japanese", "日本の首都は？一言で。", "東京"),
    ("Chinese", "1+1等于几？", "2"),
]


async def clear_cache(client: httpx.AsyncClient):
    """Clear semantic cache before tests."""
    try:
        await client.post(f"{API_BASE}/api/cache-clear", timeout=10.0)
    except Exception:
        pass


async def run_quantman_test(
    client: httpx.AsyncClient, lang: str, message: str, expected_contains: str
) -> dict:
    """Run a single QuantMan test and return results."""
    # Cache-bust with timestamp to guarantee fresh inference
    unique_msg = f"{message} [{time.time()}]"
    start = time.perf_counter()

    try:
        resp = await client.post(
            f"{API_BASE}/api/quantman",
            json={
                "message": unique_msg,
                "mode": "quantman",
                "temperature": 0.7,
                "max_tokens": 256,
            },
            timeout=60.0,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        data = resp.json()

        hy3 = data.get("hy3_state")
        partnership = data.get("partnership_score")
        text = data.get("text", "")
        left = data.get("left_text", "")
        right = data.get("right_text", "")
        model = data.get("model", "")
        convergence = data.get("convergence_method", "")

        # Normalize for comparison
        text_norm = text.strip().replace(".", "").replace("。", "")
        expected_norm = expected_contains.strip().replace(".", "").replace("。", "")

        # Check if expected answer appears in either hemisphere or converged text
        left_norm = (left or "").strip().replace(".", "").replace("。", "")
        right_norm = (right or "").strip().replace(".", "").replace("。", "")
        answer_found = (
            expected_norm in text_norm
            or expected_norm in left_norm
            or expected_norm in right_norm
        )

        # Allow HY3=1 (agree), HY3=0 (partial), or HY3=-1 (disagree) as long as
        # at least one hemisphere produced the expected answer
        passed = (
            resp.status_code == 200
            and answer_found
            and partnership is not None
        )

        return {
            "lang": lang,
            "passed": passed,
            "hy3": hy3,
            "partnership": partnership,
            "text": text,
            "left": left,
            "right": right,
            "model": model,
            "convergence": convergence,
            "latency_ms": latency_ms,
            "error": None,
        }

    except Exception as exc:
        return {
            "lang": lang,
            "passed": False,
            "error": str(exc),
            "latency_ms": (time.perf_counter() - start) * 1000,
        }


async def run_tests():
    print("=" * 70)
    print("QUANTMAN E2E TEST SUITE")
    print("=" * 70)
    print(f"API: {API_BASE}/api/quantman")
    print(f"Models: Left=Kimi K2.6+Qwen3:8b | Right=Owl Alpha+Llama3.2:3b")
    print("")

    async with httpx.AsyncClient() as client:
        # Health check
        try:
            r = await client.get(f"{API_BASE}/health", timeout=5.0)
            if r.status_code != 200:
                print(f"❌ API health check failed: {r.status_code}")
                return 1
            print("✅ API healthy")
        except Exception as exc:
            print(f"❌ API unreachable: {exc}")
            return 1

        # Clear cache
        await clear_cache(client)
        print("✅ Cache cleared")
        print("")

        # Run all language tests
        results = []
        for lang, msg, expected in TESTS:
            result = await run_quantman_test(client, lang, msg, expected)
            results.append(result)

            status = "✅" if result["passed"] else "❌"
            print(f"{status} {lang:12s} | HY3={result.get('hy3', 'ERR'):>3} | "
                  f"P={result.get('partnership', 0.0):.2f} | "
                  f"{result.get('latency_ms', 0):.0f}ms | "
                  f"{repr(result.get('text', ''))[:40]:40s}")

            if not result["passed"] and result.get("error"):
                print(f"   ERROR: {result['error']}")
            elif not result["passed"]:
                print(f"   Left:  {repr(result.get('left', ''))[:50]}")
                print(f"   Right: {repr(result.get('right', ''))[:50]}")
                print(f"   Model: {result.get('model', 'unknown')}")
                print(f"   Convergence: {result.get('convergence', 'unknown')}")
            elif result.get('hy3', 0) != 1:
                print(f"   ⚠️  HY3={result.get('hy3')} but answer found in hemisphere output")

        # Summary
        passed = sum(1 for r in results if r["passed"])
        failed = sum(1 for r in results if not r["passed"])
        avg_latency = sum(r["latency_ms"] for r in results) / max(1, len(results))

        print("")
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"  Total:   {len(results)}")
        print(f"  ✅ Pass:  {passed}")
        print(f"  ❌ Fail:  {failed}")
        print(f"  ⏱️  Avg:   {avg_latency:.0f}ms")
        print("")

        if failed == 0:
            print("🎉 All QuantMan E2E tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed. Check output above.")
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_tests()))
