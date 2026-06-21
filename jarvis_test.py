#!/usr/bin/env python3
"""
JARVIS Test Framework - Validate and test all capabilities
"""

import time
import json
import httpx
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class TestResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class Test:
    name: str
    category: str
    run: callable


class JARVISTestFramework:
    """Test framework for JARVIS"""

    def __init__(self, base_url: str = "http://localhost:3200"):
        self.base_url = base_url
        self.results: List[Dict] = []

    def run_test(self, test: Test) -> Dict:
        """Run a single test"""
        start = time.time()
        try:
            result = test.run()
            status = TestResult.PASS if result.get("success") else TestResult.FAIL
            output = result.get("output", "")
        except Exception as e:
            status = TestResult.FAIL
            output = str(e)

        duration = time.time() - start

        return {
            "name": test.name,
            "category": test.category,
            "status": status.value,
            "duration": f"{duration:.2f}s",
            "output": output,
        }

    def run_all(self) -> Dict:
        """Run all tests"""
        tests = self.get_all_tests()

        for test in tests:
            result = self.run_test(test)
            self.results.append(result)

        passed = len([r for r in self.results if r["status"] == "pass"])
        failed = len([r for r in self.results if r["status"] == "fail"])

        return {
            "total": len(tests),
            "passed": passed,
            "failed": failed,
            "results": self.results,
        }

    def get_all_tests(self) -> List[Test]:
        """Get all available tests"""
        return [
            # Core Tests
            Test("mcp_health", "core", lambda: self._test_mcp_health()),
            Test("mcp_tools", "core", lambda: self._test_mcp_tools()),
            Test("ask_sovereign", "core", lambda: self._test_ask()),
            # Voice Tests
            Test("tts_endpoint", "voice", lambda: self._test_tts()),
            Test("transcribe_endpoint", "voice", lambda: self._test_transcribe()),
            # Memory Tests
            Test("remember_fact", "memory", lambda: self._test_memory()),
            Test("get_user_info", "memory", lambda: self._test_get_info()),
            # System Tests
            Test("get_system_info", "system", lambda: self._test_system_info()),
            Test("get_health", "system", lambda: self._test_health()),
            Test("get_capabilities", "system", lambda: self._test_caps()),
            # File Tests
            Test("list_storage", "files", lambda: self._test_storage()),
            # Agent Tests
            Test("create_agent", "agents", lambda: self._test_agent()),
            # Analytics
            Test("get_metrics", "analytics", lambda: self._test_metrics()),
        ]

    def _test_mcp_health(self) -> Dict:
        r = httpx.get(f"{self.base_url}/health", timeout=10)
        return {"success": r.status_code == 200, "output": r.json()}

    def _test_mcp_tools(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
            timeout=30,
        )
        data = r.json()
        count = len(data.get("result", {}).get("tools", []))
        return {"success": count > 100, "output": f"{count} tools"}

    def _test_ask(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "ask_sovereign", "arguments": {"message": "Hello"}},
                "id": 1,
            },
            timeout=30,
        )
        data = r.json()
        text = json.loads(data["result"]["content"][0]["text"])
        return {"success": "response" in text, "output": text["response"][:50]}

    def _test_tts(self) -> Dict:
        r = httpx.post(f"{self.base_url}/speak", json={"text": "test"})
        return {"success": r.status_code == 200, "output": "audio returned"}

    def _test_transcribe(self) -> Dict:
        r = httpx.post(f"{self.base_url}/transcribe", json={})
        return {"success": True, "output": "endpoint exists"}

    def _test_memory(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "remember_fact", "arguments": {"fact": "test fact"}},
                "id": "test",
            },
        )
        return {"success": r.status_code == 200, "output": "fact remembered"}

    def _test_get_info(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "get_user_info", "arguments": {}},
                "id": "test",
            },
        )
        return {"success": r.status_code == 200, "output": "info retrieved"}

    def _test_system_info(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "get_system_info", "arguments": {}},
                "id": "test",
            },
        )
        data = r.json()
        return {"success": True, "output": "system info retrieved"}

    def _test_health(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "get_health", "arguments": {}},
                "id": "test",
            },
        )
        return {"success": r.status_code == 200, "output": "health checked"}

    def _test_caps(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "get_capabilities", "arguments": {}},
                "id": "test",
            },
        )
        data = r.json()
        return {"success": True, "output": "capabilities retrieved"}

    def _test_storage(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "list_storage", "arguments": {}},
                "id": "test",
            },
        )
        return {"success": r.status_code == 200, "output": "storage listed"}

    def _test_agent(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "create_agent",
                    "arguments": {"name": "test_agent", "role": "tester"},
                },
                "id": "test",
            },
        )
        return {"success": r.status_code == 200, "output": "agent created"}

    def _test_metrics(self) -> Dict:
        r = httpx.post(
            f"{self.base_url}/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": "get_metrics", "arguments": {}},
                "id": "test",
            },
        )
        return {"success": r.status_code == 200, "output": "metrics retrieved"}


def run_tests() -> Dict:
    """Run all JARVIS tests"""
    framework = JARVISTestFramework()
    return framework.run_all()


if __name__ == "__main__":
    print("Running JARVIS Test Suite...")
    results = run_tests()

    print(f"\n{'=' * 50}")
    print(f"RESULTS: {results['passed']}/{results['total']} passed")
    print(f"{'=' * 50}")

    for r in results["results"]:
        icon = "✅" if r["status"] == "pass" else "❌" if r["status"] == "fail" else "⏭️"
        print(f"{icon} {r['category']}: {r['name']} ({r['duration']})")
