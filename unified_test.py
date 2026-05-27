#!/usr/bin/env python3
"""
MEOK AI Labs - Unified Test Suite
Integrates: E2E Tests + JARVIS Framework + Voice Tests + Module Tests

Run: python unified_test.py [--category core|memory|voice|agents|all]
"""

import asyncio
import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess

    subprocess.run([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

# Icons
PASS = "✅"
FAIL = "❌"
SKIP = "⚠️ "
INFO = "ℹ️"


class TestStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class TestResult:
    """Single test result"""

    name: str
    category: str
    status: TestStatus
    duration: float = 0.0
    detail: str = ""
    error: str = ""


@dataclass
class TestSuite:
    """Collection of related tests"""

    name: str
    description: str
    tests: List[Callable] = field(default_factory=list)


class UnifiedTestRunner:
    """Unified test runner for all MEOK components"""

    def __init__(self, base_url: str = "http://localhost:3200"):
        self.base_url = base_url
        self.results: List[TestResult] = []
        self.start_time = 0
        self.end_time = 0

    # ==================== CORE TESTS ====================

    async def test_mcp_health(self) -> TestResult:
        """Test MCP server health endpoint"""
        start = time.time()
        try:
            r = httpx.get(f"{self.base_url}/health", timeout=10)
            body = r.json()
            duration = time.time() - start
            if r.status_code == 200 and body.get("status") in ("ok", "healthy"):
                return TestResult(
                    "mcp_health",
                    "core",
                    TestStatus.PASS,
                    duration,
                    f"status={body.get('status')}",
                )
            return TestResult(
                "mcp_health",
                "core",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "mcp_health", "core", TestStatus.FAIL, time.time() - start, "", str(e)
            )

    async def test_mcp_tools_list(self) -> TestResult:
        """Test MCP tools list"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1},
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "mcp_tools_list",
                    "core",
                    TestStatus.PASS,
                    duration,
                    "tools endpoint accessible",
                )
            return TestResult(
                "mcp_tools_list",
                "core",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "mcp_tools_list",
                "core",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_ask_sovereign(self) -> TestResult:
        """Test ask_sovereign tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "ask_sovereign",
                        "arguments": {"message": "Hello"},
                    },
                    "id": 1,
                },
                timeout=30,
            )
            duration = time.time() - start
            if r.status_code == 200:
                data = r.json()
                content = data.get("result", {}).get("content", [{}])[0].get("text", "")
                return TestResult(
                    "ask_sovereign",
                    "core",
                    TestStatus.PASS,
                    duration,
                    f"response: {content[:50]}...",
                )
            return TestResult(
                "ask_sovereign",
                "core",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "ask_sovereign",
                "core",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_get_system_status(self) -> TestResult:
        """Test get_system_status tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "get_system_status", "arguments": {}},
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "get_system_status",
                    "core",
                    TestStatus.PASS,
                    duration,
                    "system_status returned",
                )
            return TestResult(
                "get_system_status",
                "core",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "get_system_status",
                "core",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    # ==================== MEMORY TESTS ====================

    async def test_record_memory(self) -> TestResult:
        """Test record_memory tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "record_memory",
                        "arguments": {
                            "content": f"Test memory {datetime.now().isoformat()}",
                            "source_agent": "unified_test",
                            "memory_type": "insight",
                            "care_weight": 0.7,
                        },
                    },
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "record_memory",
                    "memory",
                    TestStatus.PASS,
                    duration,
                    "memory recorded",
                )
            return TestResult(
                "record_memory",
                "memory",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "record_memory",
                "memory",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_query_memories(self) -> TestResult:
        """Test query_memories tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "query_memories",
                        "arguments": {"query": "test"},
                    },
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                data = r.json()
                mems = data.get("result", {}).get("content", [{}])[0].get("text", "{}")
                mems_parsed = json.loads(mems)
                count = len(mems_parsed.get("memories", []))
                return TestResult(
                    "query_memories",
                    "memory",
                    TestStatus.PASS,
                    duration,
                    f"found {count} memories",
                )
            return TestResult(
                "query_memories",
                "memory",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "query_memories",
                "memory",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_list_memories(self) -> TestResult:
        """Test list_memories tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "list_memories", "arguments": {"limit": 5}},
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "list_memories",
                    "memory",
                    TestStatus.PASS,
                    duration,
                    "memories listed",
                )
            return TestResult(
                "list_memories",
                "memory",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "list_memories",
                "memory",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    # ==================== CONSCIOUSNESS TESTS ====================

    async def test_get_consciousness_state(self) -> TestResult:
        """Test get_consciousness_state tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "get_consciousness_state", "arguments": {}},
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                data = r.json()
                content = (
                    data.get("result", {}).get("content", [{}])[0].get("text", "{}")
                )
                parsed = json.loads(content)
                mode = parsed.get("mode") or parsed.get("consciousness_mode", "unknown")
                return TestResult(
                    "get_consciousness_state",
                    "consciousness",
                    TestStatus.PASS,
                    duration,
                    f"mode={mode}",
                )
            return TestResult(
                "get_consciousness_state",
                "consciousness",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "get_consciousness_state",
                "consciousness",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_assess_care_safety(self) -> TestResult:
        """Test assess_care_safety tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "assess_care_safety",
                        "arguments": {"text": "I need help"},
                    },
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "assess_care_safety",
                    "consciousness",
                    TestStatus.PASS,
                    duration,
                    "safety assessed",
                )
            return TestResult(
                "assess_care_safety",
                "consciousness",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "assess_care_safety",
                "consciousness",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    # ==================== VISION TOOLS TESTS ====================

    async def test_capture_screenshot(self) -> TestResult:
        """Test capture_screenshot tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "capture_screenshot", "arguments": {}},
                    "id": 1,
                },
                timeout=15,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "capture_screenshot",
                    "vision",
                    TestStatus.PASS,
                    duration,
                    "screenshot captured",
                )
            return TestResult(
                "capture_screenshot",
                "vision",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "capture_screenshot",
                "vision",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_analyze_screenshot(self) -> TestResult:
        """Test analyze_screenshot tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "analyze_screenshot",
                        "arguments": {"prompt": "What do you see?"},
                    },
                    "id": 1,
                },
                timeout=30,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "analyze_screenshot",
                    "vision",
                    TestStatus.PASS,
                    duration,
                    "screenshot analyzed",
                )
            return TestResult(
                "analyze_screenshot",
                "vision",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "analyze_screenshot",
                "vision",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    # ==================== SYSTEM TOOLS TESTS ====================

    async def test_run_command(self) -> TestResult:
        """Test run_command tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "run_command",
                        "arguments": {"command": "echo hello"},
                    },
                    "id": 1,
                },
                timeout=15,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "run_command",
                    "system",
                    TestStatus.PASS,
                    duration,
                    "command executed",
                )
            return TestResult(
                "run_command",
                "system",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "run_command",
                "system",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_list_files(self) -> TestResult:
        """Test list_files tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "list_files", "arguments": {"path": "/tmp"}},
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "list_files", "system", TestStatus.PASS, duration, "files listed"
                )
            return TestResult(
                "list_files",
                "system",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "list_files", "system", TestStatus.FAIL, time.time() - start, "", str(e)
            )

    # ==================== AGENT TESTS ====================

    async def test_create_agent(self) -> TestResult:
        """Test create_agent tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "create_agent",
                        "arguments": {
                            "name": f"test_agent_{int(time.time())}",
                            "description": "Test agent",
                            "capabilities": ["test"],
                        },
                    },
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "create_agent", "agents", TestStatus.PASS, duration, "agent created"
                )
            return TestResult(
                "create_agent",
                "agents",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "create_agent",
                "agents",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_list_agents(self) -> TestResult:
        """Test list_agents tool"""
        start = time.time()
        try:
            r = httpx.post(
                f"{self.base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {"name": "list_agents", "arguments": {}},
                    "id": 1,
                },
                timeout=10,
            )
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "list_agents", "agents", TestStatus.PASS, duration, "agents listed"
                )
            return TestResult(
                "list_agents",
                "agents",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "list_agents",
                "agents",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    # ==================== EXTERNAL SERVICES TESTS ====================

    async def test_ollama_health(self) -> TestResult:
        """Test Ollama service"""
        start = time.time()
        try:
            r = httpx.get("http://localhost:11434/", timeout=5)
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "ollama_health",
                    "external",
                    TestStatus.PASS,
                    duration,
                    f"status={r.status_code}",
                )
            return TestResult(
                "ollama_health",
                "external",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "ollama_health",
                "external",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_ollama_models(self) -> TestResult:
        """Test Ollama models list"""
        start = time.time()
        try:
            r = httpx.get("http://localhost:11434/api/tags", timeout=10)
            duration = time.time() - start
            if r.status_code == 200:
                models = r.json().get("models", [])
                return TestResult(
                    "ollama_models",
                    "external",
                    TestStatus.PASS,
                    duration,
                    f"{len(models)} models",
                )
            return TestResult(
                "ollama_models",
                "external",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "ollama_models",
                "external",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    async def test_meok_ui(self) -> TestResult:
        """Test MEOK Web UI"""
        start = time.time()
        try:
            r = httpx.get("http://localhost:3000/", timeout=10)
            duration = time.time() - start
            if r.status_code == 200:
                return TestResult(
                    "meok_ui",
                    "external",
                    TestStatus.PASS,
                    duration,
                    f"content_length={len(r.text)}",
                )
            return TestResult(
                "meok_ui",
                "external",
                TestStatus.FAIL,
                duration,
                "",
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "meok_ui", "external", TestStatus.FAIL, time.time() - start, "", str(e)
            )

    async def test_voice_server(self) -> TestResult:
        """Test Voice WebSocket server"""
        start = time.time()
        try:
            r = httpx.get("http://localhost:8765/health", timeout=5)
            duration = time.time() - start
            return TestResult(
                "voice_server",
                "external",
                TestStatus.PASS,
                duration,
                f"status={r.status_code}",
            )
        except Exception as e:
            return TestResult(
                "voice_server",
                "external",
                TestStatus.SKIP,
                time.time() - start,
                "",
                f"Voice server not available: {str(e)[:30]}",
            )

    # ==================== MODULE TESTS ====================

    def test_semantic_cache_module(self) -> TestResult:
        """Test semantic cache module"""
        start = time.time()
        try:
            from jarvis_semantic_cache import SemanticCache

            cache = SemanticCache(similarity_threshold=0.8)
            cache.set("test request", "test response")
            result = cache.get("test request")
            duration = time.time() - start
            if result == "test response":
                return TestResult(
                    "semantic_cache_module",
                    "modules",
                    TestStatus.PASS,
                    duration,
                    "cache working",
                )
            return TestResult(
                "semantic_cache_module",
                "modules",
                TestStatus.FAIL,
                duration,
                "",
                "cache mismatch",
            )
        except Exception as e:
            return TestResult(
                "semantic_cache_module",
                "modules",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    def test_department_agents_module(self) -> TestResult:
        """Test department agents module"""
        start = time.time()
        try:
            from department_agents_v2 import CEOAgent

            duration = time.time() - start
            return TestResult(
                "department_agents_module",
                "modules",
                TestStatus.PASS,
                duration,
                "agents imported",
            )
        except Exception as e:
            return TestResult(
                "department_agents_module",
                "modules",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    def test_orchestrator_module(self) -> TestResult:
        """Test orchestrator module"""
        start = time.time()
        try:
            from jarvis_orchestrator_v2 import OrchestratorConfig, JARVISOrchestrator

            config = OrchestratorConfig()
            duration = time.time() - start
            return TestResult(
                "orchestrator_module",
                "modules",
                TestStatus.PASS,
                duration,
                "orchestrator imported",
            )
        except Exception as e:
            return TestResult(
                "orchestrator_module",
                "modules",
                TestStatus.FAIL,
                time.time() - start,
                "",
                str(e),
            )

    # ==================== RUNNER ====================

    async def run_category(self, category: str) -> List[TestResult]:
        """Run tests for a specific category"""
        tests_map = {
            "core": [
                self.test_mcp_health,
                self.test_mcp_tools_list,
                self.test_ask_sovereign,
                self.test_get_system_status,
            ],
            "memory": [
                self.test_record_memory,
                self.test_query_memories,
                self.test_list_memories,
            ],
            "consciousness": [
                self.test_get_consciousness_state,
                self.test_assess_care_safety,
            ],
            "vision": [
                self.test_capture_screenshot,
                self.test_analyze_screenshot,
            ],
            "system": [
                self.test_run_command,
                self.test_list_files,
            ],
            "agents": [
                self.test_create_agent,
                self.test_list_agents,
            ],
            "external": [
                self.test_ollama_health,
                self.test_ollama_models,
                self.test_meok_ui,
                self.test_voice_server,
            ],
            "modules": [
                lambda: self.test_semantic_cache_module(),
                lambda: self.test_department_agents_module(),
                lambda: self.test_orchestrator_module(),
            ],
        }

        if category == "all":
            all_tests = []
            for cat_tests in tests_map.values():
                all_tests.extend(cat_tests)
            tests = all_tests
        else:
            tests = tests_map.get(category, [])

        results = []
        for test in tests:
            try:
                # Handle both async and sync tests
                if asyncio.iscoroutinefunction(test):
                    result = await test()
                else:
                    result = test()
                results.append(result)
            except Exception as e:
                results.append(
                    TestResult("unknown", category, TestStatus.FAIL, 0, "", str(e))
                )

        return results

    async def run_all(self, categories: List[str] = None) -> Dict:
        """Run all tests"""
        self.start_time = time.time()

        if categories is None:
            categories = [
                "core",
                "memory",
                "consciousness",
                "vision",
                "system",
                "agents",
                "external",
                "modules",
            ]

        print(f"\n{'=' * 70}")
        print(f"MEOK AI Labs - Unified Test Suite")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 70}\n")

        for category in categories:
            print(f"[{category.upper()}]")
            results = await self.run_category(category)
            for r in results:
                icon = (
                    PASS
                    if r.status == TestStatus.PASS
                    else (FAIL if r.status == TestStatus.FAIL else SKIP)
                )
                print(f"  {icon} {r.name} ({r.duration:.0f}ms) {r.detail}")
                self.results.append(r)
            print()

        self.end_time = time.time()

        return self.get_summary()

    def get_summary(self) -> Dict:
        """Get test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIP)

        total_time = self.end_time - self.start_time

        # Group by category
        by_category = {}
        for r in self.results:
            if r.category not in by_category:
                by_category[r.category] = {"pass": 0, "fail": 0, "skip": 0}
            by_category[r.category][r.status.value] += 1

        print(f"{'=' * 70}")
        print(f"SUMMARY")
        print(f"{'=' * 70}")
        print(f"Total: {total} | {PASS} {passed} | {FAIL} {failed} | {SKIP} {skipped}")
        print(f"Time: {total_time:.1f}s")
        print(f"\nBy Category:")
        for cat, stats in by_category.items():
            print(
                f"  {cat}: {stats['pass']} pass, {stats['fail']} fail, {stats['skip']} skip"
            )

        if failed > 0:
            print(f"\nFailed Tests:")
            for r in self.results:
                if r.status == TestStatus.FAIL:
                    print(f"  - {r.name}: {r.error}")

        print(f"{'=' * 70}\n")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": total_time,
            "by_category": by_category,
        }


async def main():
    parser = argparse.ArgumentParser(description="MEOK AI Labs Unified Test Suite")
    parser.add_argument(
        "--category",
        default="all",
        help="Test category: core|memory|consciousness|vision|system|agents|external|modules|all",
    )
    parser.add_argument("--categories", nargs="+", help="Multiple categories to run")
    args = parser.parse_args()

    runner = UnifiedTestRunner()

    if args.categories:
        results = await runner.run_all(args.categories)
    else:
        results = await runner.run_all([args.category])

    sys.exit(1 if results["failed"] > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
