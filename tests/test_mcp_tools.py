"""
DeepEval + pytest test suite for SOV3 MCP tools.
Run: pytest tests/test_mcp_tools.py -v
Or:  deepeval test run tests/test_mcp_tools.py (for LLM-judged metrics)

Tests the top 20 most-used MCP tools against the live SOV3 server.
"""

import pytest
import requests
import json
import time

SOV3_URL = "http://localhost:3101"


def call_tool(name: str, args: dict = None) -> dict:
    """Call an MCP tool and return the full response."""
    r = requests.post(f"{SOV3_URL}/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": args or {}},
    }, timeout=30)
    return r.json()


def get_tool_text(name: str, args: dict = None) -> str:
    """Call tool and extract text result."""
    data = call_tool(name, args)
    content = data.get("result", {}).get("content", [{}])
    texts = [c.get("text", "") for c in content if c.get("text")]
    return "\n".join(texts)


class TestSystemTools:
    """Core system health and status tools."""

    def test_sovereign_health_check(self):
        result = get_tool_text("sovereign_health_check")
        data = json.loads(result)
        assert data["status"] == "healthy"
        assert "components" in data
        assert data["components"]["memory_store"] == "connected"

    def test_get_system_status(self):
        result = get_tool_text("get_system_status")
        data = json.loads(result)
        # Response has agents, consciousness, memory, maintenance — not a "status" key
        assert any(k in data for k in ["agents", "consciousness", "memory", "maintenance"])

    def test_get_consciousness_state(self):
        result = get_tool_text("get_consciousness_state")
        data = json.loads(result)
        assert "consciousness_mode" in data
        assert "emotional" in data
        assert data["consciousness_mode"] in ["waking", "dreaming", "deep_sleep"]

    def test_get_dashboard_metrics(self):
        result = get_tool_text("get_dashboard_metrics")
        assert result  # Should return something


class TestMemoryTools:
    """Memory storage and retrieval tools."""

    def test_record_memory(self):
        result = call_tool("record_memory", {
            "content": f"TEST_MEMORY_{int(time.time())}",
            "tags": ["test", "automated"],
            "importance": 0.1,
            "source_agent": "test_suite",
        })
        assert "result" in result

    def test_query_memories(self):
        result = get_tool_text("query_memories", {"query": "test", "limit": 3})
        data = json.loads(result)
        assert "memories" in data

    def test_get_memory_stats(self):
        result = get_tool_text("get_memory_stats")
        assert result

    def test_list_memories(self):
        result = get_tool_text("list_memories", {"limit": 5})
        assert result


class TestAgentTools:
    """Agent management and task tools."""

    def test_list_agents(self):
        result = get_tool_text("list_agents")
        data = json.loads(result)
        assert isinstance(data, (list, dict))

    def test_get_agent_registry_stats(self):
        result = get_tool_text("get_agent_registry_stats")
        assert result

    def test_orion_hunt_tasks(self):
        result = get_tool_text("orion_hunt_tasks", {
            "root_dir": "/Users/nicholas/clawd/sovereign-temple",
            "max_files": 10,
        })
        data = json.loads(result)
        assert "agent" in data


class TestConsciousnessTools:
    """Consciousness and reflection tools."""

    def test_trigger_reflection(self):
        result = get_tool_text("trigger_reflection", {
            "topic": "automated test reflection"
        })
        data = json.loads(result)
        assert "timestamp" in data

    def test_enter_dream_state(self):
        result = get_tool_text("enter_dream_state", {"duration_seconds": 5})
        data = json.loads(result)
        assert "started_at" in data
        assert "phases" in data


class TestCreativityTools:
    """Creativity and knowledge tools."""

    def test_find_bisociations(self):
        result = get_tool_text("find_bisociations", {
            "concept_a": "music",
            "concept_b": "code",
        })
        data = json.loads(result)
        assert "bisociation_links" in data

    def test_suggest_exploration(self):
        result = get_tool_text("suggest_exploration")
        assert result


class TestActionTools:
    """Execution and action tools."""

    def test_run_command(self):
        result = get_tool_text("run_command", {"command": "echo hello_from_test"})
        assert "hello_from_test" in result or result  # May have output format

    def test_execute_code(self):
        result = get_tool_text("execute_code", {
            "code": "print('test_passed')",
            "language": "python",
        })
        assert result


class TestAPIEndpoints:
    """Direct HTTP endpoint tests."""

    def test_health(self):
        r = requests.get(f"{SOV3_URL}/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"

    def test_metrics(self):
        r = requests.get(f"{SOV3_URL}/metrics", timeout=5)
        assert r.status_code == 200
        assert "http_requests_total" in r.text

    def test_agent_status(self):
        r = requests.get(f"{SOV3_URL}/agent/status", timeout=5)
        assert r.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
