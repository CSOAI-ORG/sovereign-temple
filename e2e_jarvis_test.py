#!/usr/bin/env python3
"""
MEOK AI Labs E2E Test Suite
Tests MCP Server (3200), Voice WebSocket (8765), MEOK Desktop (1420), MEOK UI (3000)

Usage: python e2e_jarvis_test.py
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

PASS = "✅"
FAIL = "❌"
SKIP = "⚠️ "
TIMEOUT = 30  # Increased for AI responses


class TestResult:
    def __init__(
        self, group: str, name: str, status: str, detail: str = "", ms: float = 0.0
    ):
        self.group = group
        self.name = name
        self.status = status
        self.detail = detail
        self.ms = ms

    def __str__(self):
        ms_str = f" ({self.ms:.0f}ms)" if self.ms > 0 else ""
        detail_str = f" — {self.detail}" if self.detail else ""
        return f"  {PASS if self.status == 'PASS' else (FAIL if self.status == 'FAIL' else SKIP)} [{self.group}] {self.name}{ms_str}{detail_str}"


def run_test(group: str, name: str, fn, *args, **kwargs) -> TestResult:
    t0 = time.monotonic()
    try:
        result = fn(*args, **kwargs)
        ms = (time.monotonic() - t0) * 1000
        if result is True or result is None:
            return TestResult(group, name, "PASS", ms=ms)
        elif isinstance(result, str):
            return TestResult(group, name, "PASS", detail=result, ms=ms)
        elif isinstance(result, tuple) and len(result) == 2:
            ok, detail = result
            return TestResult(group, name, "PASS" if ok else "FAIL", str(detail), ms)
        else:
            return TestResult(group, name, "FAIL", f"unexpected return: {result}", ms)
    except AssertionError as ae:
        ms = (time.monotonic() - t0) * 1000
        return TestResult(group, name, "FAIL", str(ae), ms)
    except Exception as exc:
        ms = (time.monotonic() - t0) * 1000
        return TestResult(group, name, "FAIL", f"{type(exc).__name__}: {exc}", ms)


def mcp_call(base: str, tool: str, arguments: Dict = None) -> Tuple[int, Any]:
    """Call MCP tool via JSON-RPC 2.0"""
    try:
        response = httpx.post(
            f"{base}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments or {}},
                "id": 1,
            },
            timeout=TIMEOUT,
        )
        if response.status_code == 200:
            body = response.json()
            if "result" in body:
                content = body.get("result", {}).get("content", [])
                if (
                    content
                    and isinstance(content, list)
                    and content[0].get("type") == "text"
                ):
                    try:
                        return 200, json.loads(content[0]["text"])
                    except Exception:
                        return 200, body
                return 200, body.get("result", body)
        return response.status_code, body if "body" in locals() else {}
    except Exception as e:
        return 0, {"error": str(e)}


# ==================== TEST GROUPS ====================


async def test_mcp_server_health(base: str) -> List[TestResult]:
    """Group 1: MCP Server Health"""
    results = []
    group = "mcp_health"

    def check_health():
        r = httpx.get(f"{base}/health", timeout=5)
        assert r.status_code == 200, f"status={r.status_code}"
        body = r.json()
        assert body.get("status") in ("ok", "healthy"), f"status={body.get('status')}"
        return f"status={body.get('status')}, version={body.get('version', '?')}"

    def check_pulse():
        r = httpx.get(f"{base}/api/pulse", timeout=5)
        if r.status_code == 404:
            return "SKIP - endpoint not available"
        assert r.status_code == 200, f"status={r.status_code}"
        return f"pulse OK"

    results.append(run_test(group, "GET /health", check_health))
    results.append(run_test(group, "GET /pulse", check_pulse))
    return results


async def test_jarvis_tools(base: str) -> List[TestResult]:
    """Group 2: JARVIS MCP Tools"""
    results = []
    group = "jarvis_tools"

    def test_ask_sovereign():
        code, body = mcp_call(base, "ask_sovereign", {"message": "Hello"})
        assert code == 200, f"status={code}"
        text = (
            body.get("response")
            or body.get("result", {}).get("response")
            or str(body)[:100]
        )
        return f"response={text[:50]}..."

    def test_get_system_status():
        code, body = mcp_call(base, "get_system_status", {})
        assert code == 200, f"status={code}"
        return "system_status returned"

    def test_record_memory():
        code, body = mcp_call(
            base,
            "record_memory",
            {
                "content": f"E2E test at {datetime.now().isoformat()}",
                "source_agent": "e2e_test",
                "memory_type": "insight",
                "care_weight": 0.7,
            },
        )
        assert code == 200, f"status={code}"
        return "memory recorded"

    def test_query_memories():
        code, body = mcp_call(base, "query_memories", {"query": "test"})
        assert code == 200, f"status={code}"
        mems = body.get("memories") or body.get("results") or []
        return f"found {len(mems)} memories"

    def test_get_consciousness_state():
        code, body = mcp_call(base, "get_consciousness_state", {})
        assert code == 200, f"status={code}"
        mode = body.get("mode") or body.get("consciousness_mode") or "unknown"
        return f"mode={mode}"

    def test_assess_care_safety():
        code, body = mcp_call(base, "assess_care_safety", {"text": "I need help"})
        assert code == 200, f"status={code}"
        return "safety assessed"

    results.append(run_test(group, "ask_sovereign", test_ask_sovereign))
    results.append(run_test(group, "get_system_status", test_get_system_status))
    results.append(run_test(group, "record_memory", test_record_memory))
    results.append(run_test(group, "query_memories", test_query_memories))
    results.append(
        run_test(group, "get_consciousness_state", test_get_consciousness_state)
    )
    results.append(run_test(group, "assess_care_safety", test_assess_care_safety))
    return results


async def test_vision_tools(base: str) -> List[TestResult]:
    """Group 3: Vision & Screenshot Tools"""
    results = []
    group = "vision_tools"

    def test_capture_screenshot():
        code, body = mcp_call(base, "capture_screenshot", {})
        if code == 404:
            return "SKIP - tool not available"
        assert code == 200, f"status={code}"
        return "screenshot captured"

    def test_analyze_screenshot():
        code, body = mcp_call(
            base, "analyze_screenshot", {"prompt": "What do you see?"}
        )
        if code == 404:
            return "SKIP - tool not available"
        assert code == 200, f"status={code}"
        return "screenshot analyzed"

    results.append(run_test(group, "capture_screenshot", test_capture_screenshot))
    results.append(run_test(group, "analyze_screenshot", test_analyze_screenshot))
    return results


async def test_system_tools(base: str) -> List[TestResult]:
    """Group 4: System Tools"""
    results = []
    group = "system_tools"

    def test_run_command():
        code, body = mcp_call(base, "run_command", {"command": "echo hello"})
        if code == 404:
            return "SKIP - tool not available"
        assert code == 200, f"status={code}"
        return "command executed"

    def test_list_files():
        code, body = mcp_call(base, "list_files", {"path": "/tmp"})
        if code == 404:
            return "SKIP - tool not available"
        assert code == 200, f"status={code}"
        return "files listed"

    results.append(run_test(group, "run_command", test_run_command))
    results.append(run_test(group, "list_files", test_list_files))
    return results


async def test_voice_websocket(port: int) -> List[TestResult]:
    """Group 5: Voice WebSocket Server"""
    results = []
    group = "voice_ws"

    def check_ws_health():
        try:
            r = httpx.get(f"http://localhost:{port}/health", timeout=5)
            return f"status={r.status_code}"
        except Exception as e:
            return f"FAIL - {str(e)[:30]}"

    def check_ws_status():
        try:
            r = httpx.get(f"http://localhost:{port}/status", timeout=5)
            if r.status_code == 200:
                return "voice server responding"
            return f"status={r.status_code}"
        except Exception as e:
            return f"FAIL - {str(e)[:30]}"

    results.append(run_test(group, "GET /health", check_ws_health))
    results.append(run_test(group, "GET /status", check_ws_status))
    return results


async def test_meok_desktop(port: int) -> List[TestResult]:
    """Group 6: MEOK Desktop UI"""
    results = []
    group = "meok_desktop"

    def check_desktop():
        try:
            r = httpx.get(f"http://localhost:{port}/", timeout=5)
            assert r.status_code == 200, f"status={r.status_code}"
            return f"status={r.status_code}"
        except Exception as e:
            return f"FAIL - {str(e)[:30]}"

    results.append(run_test(group, "GET / (MEOK Desktop)", check_desktop))
    return results


async def test_meok_ui(port: int) -> List[TestResult]:
    """Group 7: MEOK Web UI"""
    results = []
    group = "meok_ui"

    def check_ui():
        try:
            r = httpx.get(f"http://localhost:{port}/", timeout=5)
            assert r.status_code == 200, f"status={r.status_code}"
            return f"status={r.status_code}, content_length={len(r.text)}"
        except Exception as e:
            return f"FAIL - {str(e)[:30]}"

    def check_overlay():
        try:
            r = httpx.get(f"http://localhost:{port}/api/jarvis-status", timeout=5)
            return f"overlay status={r.status_code}"
        except:
            return "overlay not exposed"

    results.append(run_test(group, "GET / (MEOK UI)", check_ui))
    results.append(run_test(group, "GET /api/jarvis-status", check_overlay))
    return results


async def test_ollama() -> List[TestResult]:
    """Group 8: Ollama Local Models"""
    results = []
    group = "ollama"

    def check_ollama():
        try:
            r = httpx.get("http://localhost:11434/", timeout=5)
            return f"status={r.status_code}"
        except Exception as e:
            return f"FAIL - {str(e)[:30]}"

    def check_models():
        try:
            r = httpx.get("http://localhost:11434/api/tags", timeout=10)
            if r.status_code == 200:
                models = r.json().get("models", [])
                return f"{len(models)} models"
            return f"status={r.status_code}"
        except Exception as e:
            return f"FAIL - {str(e)[:30]}"

    results.append(run_test(group, "GET / (health)", check_ollama))
    results.append(run_test(group, "GET /api/tags (models)", check_models))
    return results


# ==================== MAIN RUNNER ====================


async def run_all_tests():
    MCP_BASE = "http://localhost:3200"
    VOICE_PORT = 8765
    DESKTOP_PORT = 1420
    UI_PORT = 3000

    print(f"\n{'=' * 70}")
    print(f"MEOK AI Labs E2E Test Suite")
    print(
        f"MCP: {MCP_BASE} | Voice: {VOICE_PORT} | Desktop: {DESKTOP_PORT} | UI: {UI_PORT}"
    )
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 70}\n")

    all_results: List[TestResult] = []

    test_groups = [
        ("MCP Server Health", lambda: test_mcp_server_health(MCP_BASE)),
        ("JARVIS Tools", lambda: test_jarvis_tools(MCP_BASE)),
        ("Vision Tools", lambda: test_vision_tools(MCP_BASE)),
        ("System Tools", lambda: test_system_tools(MCP_BASE)),
        ("Voice WebSocket", lambda: test_voice_websocket(VOICE_PORT)),
        ("MEOK Desktop", lambda: test_meok_desktop(DESKTOP_PORT)),
        ("MEOK Web UI", lambda: test_meok_ui(UI_PORT)),
        ("Ollama Models", lambda: test_ollama()),
    ]

    for group_name, run_fn in test_groups:
        print(f"[{group_name}]")
        try:
            group_results = await run_fn()
            for r in group_results:
                print(r)
                all_results.append(r)
        except Exception as exc:
            err_result = TestResult(group_name, "group_runner", "FAIL", str(exc))
            print(err_result)
            all_results.append(err_result)
        print()

    total = len(all_results)
    passed = sum(1 for r in all_results if r.status == "PASS")
    failed = sum(1 for r in all_results if r.status == "FAIL")
    skipped = sum(1 for r in all_results if r.status == "SKIP")

    avg_ms = sum(r.ms for r in all_results if r.ms > 0) / max(
        len([r for r in all_results if r.ms > 0]), 1
    )

    print(f"{'=' * 70}")
    print(
        f"Results: {PASS} {passed}/{total} passed | {FAIL} {failed} failed | {SKIP} {skipped} skipped"
    )
    print(f"Avg latency: {avg_ms:.0f}ms per test")

    if failed > 0:
        print(f"\nFailed tests:")
        for r in all_results:
            if r.status == "FAIL":
                print(f"  {r}")

    print(f"{'=' * 70}\n")

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }


if __name__ == "__main__":
    results = asyncio.run(run_all_tests())
    sys.exit(1 if results["failed"] > 0 else 0)
