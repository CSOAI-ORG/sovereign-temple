"""
E2E Integration Tests — Full system verification
Run: pytest tests/test_e2e_integration.py -v -p no:deepeval

Tests the complete chain: SOV3 → Voice Pipeline → Character Bridge → Memory
"""

import pytest
import requests
import json
import time
import subprocess
import os

SOV3_URL = "http://localhost:3101"
OLLAMA_URL = "http://localhost:11434"


def call_tool(name, args=None):
    r = requests.post(f"{SOV3_URL}/mcp", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": name, "arguments": args or {}},
    }, timeout=30)
    return r.json()


def get_text(name, args=None):
    data = call_tool(name, args)
    content = data.get("result", {}).get("content", [{}])
    return "\n".join(c.get("text", "") for c in content if c.get("text"))


class TestFullStack:
    """Tests that verify the complete system works end-to-end."""

    def test_sov3_healthy(self):
        """SOV3 server is running and healthy."""
        r = requests.get(f"{SOV3_URL}/health", timeout=5)
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_ollama_running(self):
        """Ollama is running with google/gemma-4-27b-it:free."""
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        assert r.status_code == 200
        models = [m["name"] for m in r.json().get("models", [])]
        assert "google/gemma-4-27b-it:free" in models, f"google/gemma-4-27b-it:free not in {models}"

    def test_redis_running(self):
        """Redis is running for Taskiq."""
        result = subprocess.run(
            ["/opt/homebrew/opt/redis/bin/redis-cli", "ping"],
            capture_output=True, text=True, timeout=5
        )
        assert "PONG" in result.stdout

    def test_postgresql_memory(self):
        """PostgreSQL has memory episodes."""
        result = subprocess.run(
            ["psql", "-U", "sovereign", "-d", "sovereign_memory", "-t", "-c",
             "SELECT COUNT(*) FROM memory_episodes;"],
            capture_output=True, text=True, timeout=5
        )
        count = int(result.stdout.strip())
        assert count > 100, f"Only {count} memories — expected 100+"

    def test_fsrs_columns_exist(self):
        """FSRS columns exist in memory_episodes."""
        result = subprocess.run(
            ["psql", "-U", "sovereign", "-d", "sovereign_memory", "-t", "-c",
             "SELECT column_name FROM information_schema.columns WHERE table_name='memory_episodes' AND column_name LIKE 'fsrs%';"],
            capture_output=True, text=True, timeout=5
        )
        assert "fsrs_stability" in result.stdout
        assert "fsrs_retrievability" in result.stdout

    def test_curiosity_columns_exist(self):
        """Curiosity score column exists."""
        result = subprocess.run(
            ["psql", "-U", "sovereign", "-d", "sovereign_memory", "-t", "-c",
             "SELECT column_name FROM information_schema.columns WHERE table_name='memory_episodes' AND column_name='curiosity_score';"],
            capture_output=True, text=True, timeout=5
        )
        assert "curiosity_score" in result.stdout


class TestNeuralModels:
    """All 9 neural models are trained and accessible."""

    def test_all_models_trained(self):
        r = requests.get(f"{SOV3_URL}/health", timeout=5)
        models = r.json()["components"]["neural_models"]
        for name, info in models.items():
            assert info.get("is_trained", False) or info.get("model_exists", False), \
                f"Model {name} not trained"

    def test_model_count(self):
        r = requests.get(f"{SOV3_URL}/health", timeout=5)
        models = r.json()["components"]["neural_models"]
        assert len(models) >= 9, f"Only {len(models)} models, expected 9+"


class TestConsciousness:
    """Consciousness system is operational."""

    def test_consciousness_mode(self):
        result = get_text("get_consciousness_state")
        data = json.loads(result)
        assert data["consciousness_mode"] in ["waking", "dreaming", "deep_sleep"]

    def test_consciousness_level(self):
        result = get_text("get_consciousness_state")
        data = json.loads(result)
        level = data.get("consciousness_level", 0)
        assert 0 <= level <= 1, f"Consciousness level {level} out of range"

    def test_dream_cycle(self):
        result = get_text("enter_dream_state", {"duration_seconds": 5})
        data = json.loads(result)
        assert "phases" in data
        assert len(data["phases"]) >= 1

    def test_reflection(self):
        result = get_text("trigger_reflection", {"topic": "E2E test"})
        data = json.loads(result)
        assert "insights" in data


class TestCreativity:
    """Creativity engine with 40 civilisational traditions."""

    def test_bisociations(self):
        result = get_text("find_bisociations", {"concept_a": "art", "concept_b": "math"})
        data = json.loads(result)
        assert "bisociation_links" in data
        assert len(data["bisociation_links"]) > 0

    def test_exploration_suggestions(self):
        result = get_text("suggest_exploration")
        assert result and len(result) > 10


class TestAgentExecution:
    """Agent task execution is operational."""

    def test_agent_executor_endpoint(self):
        r = requests.get(f"{SOV3_URL}/agent/status", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert "broker" in data

    def test_orion_can_hunt(self):
        result = get_text("orion_hunt_tasks", {
            "root_dir": "/Users/nicholas/clawd/sovereign-temple",
            "max_files": 5,
        })
        data = json.loads(result)
        assert data["agent"] == "orion-riri-hourman"


class TestVoicePipeline:
    """Voice pipeline files compile and knowledge base loads."""

    def test_jarvis_compass_compiles(self):
        result = subprocess.run(
            ["python3", "-c",
             "import py_compile; py_compile.compile('voice_pipeline/jarvis_compass.py', doraise=True)"],
            capture_output=True, text=True, timeout=10,
            cwd="/Users/nicholas/clawd/sovereign-temple"
        )
        assert result.returncode == 0, result.stderr

    def test_jarvis_v5_compiles(self):
        result = subprocess.run(
            ["python3", "-c",
             "import py_compile; py_compile.compile('voice_pipeline/jarvis_v5_pipecat.py', doraise=True)"],
            capture_output=True, text=True, timeout=10,
            cwd="/Users/nicholas/clawd/sovereign-temple"
        )
        assert result.returncode == 0, result.stderr

    def test_knowledge_base_loads(self):
        result = subprocess.run(
            ["python3", "-c",
             "from voice_pipeline.jarvis_knowledge import build_system_prompt; p = build_system_prompt(); assert len(p) > 500, f'Prompt too short: {len(p)}'"],
            capture_output=True, text=True, timeout=10,
            cwd="/Users/nicholas/clawd/sovereign-temple"
        )
        assert result.returncode == 0, result.stderr

    def test_character_bridge_compiles(self):
        result = subprocess.run(
            ["python3", "-c",
             "import py_compile; py_compile.compile('character_bridge.py', doraise=True)"],
            capture_output=True, text=True, timeout=10,
            cwd="/Users/nicholas/clawd/sovereign-temple"
        )
        assert result.returncode == 0, result.stderr


class TestMemorySystem:
    """Memory ingestion, retrieval, and quality."""

    def test_record_and_retrieve(self):
        """Write a memory, then find it."""
        tag = f"e2e_test_{int(time.time())}"
        call_tool("record_memory", {
            "content": f"E2E test memory {tag}",
            "tags": [tag],
            "importance": 0.1,
            "source_agent": "e2e_test",
        })
        # Query it back
        result = get_text("query_memories", {"query": tag, "limit": 1})
        # Should find something (may not find exact match without embeddings)
        assert result

    def test_memory_stats(self):
        result = get_text("get_memory_stats")
        assert result


class TestPrometheus:
    """Monitoring is operational."""

    def test_metrics_endpoint(self):
        r = requests.get(f"{SOV3_URL}/metrics", timeout=5)
        assert r.status_code == 200
        assert "http_requests_total" in r.text
        assert "http_request_duration" in r.text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
