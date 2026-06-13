"""Overnight cycle-3 tests: persistent tool telemetry + kimi local fallback."""
import os
import sys
import asyncio
import tempfile
import pathlib
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "creativity_engine"))


class TestTelemetryPersistence(unittest.TestCase):
    def test_counts_survive_a_restart(self):
        from tool_dispatcher import ToolDispatcher
        tmp = pathlib.Path(tempfile.mkdtemp()) / "tt.json"
        d = ToolDispatcher([{"name": "t1", "description": "x"}]); d._telemetry_path = tmp
        d.record_call("t1", True); d.record_call("t1", False); d.record_call("t2", True)
        # new instance = simulated restart; load from the same file
        d2 = ToolDispatcher([{"name": "t1", "description": "x"}]); d2._telemetry_path = tmp; d2._load_telemetry()
        self.assertEqual(d2.calls_total.get("t1"), 2)
        self.assertEqual(d2.errors_total.get("t1"), 1)
        self.assertEqual(d2.calls_total.get("t2"), 1)

    def test_missing_file_is_safe(self):
        from tool_dispatcher import ToolDispatcher
        d = ToolDispatcher([{"name": "t1", "description": "x"}])
        d._telemetry_path = pathlib.Path(tempfile.mkdtemp()) / "nope.json"
        d.calls_total = {}; d.errors_total = {}   # isolate from the real prod file loaded in __init__
        d._load_telemetry()           # loading a MISSING file must not raise and must leave counts empty
        self.assertEqual(d.calls_total, {})


class TestKimiFallback(unittest.TestCase):
    def test_no_key_routes_to_fallback_not_unavailable(self):
        from kimi_agent import KimiAgent
        r = asyncio.run(KimiAgent(api_key="").send_task(task_description="ping"))
        blob = (str(r.get("model", "")) + str(r.get("error", "")) + str(r.get("status", ""))).lower()
        # must take the fallback path (completed via Ollama, or a 'local fallback' error if Ollama down)
        self.assertTrue("fallback" in blob or r.get("status") == "completed", f"did not route to fallback: {r}")
        self.assertNotIn("check kimi_api_key", blob)   # must NOT be the old 'not available' failure


if __name__ == "__main__":
    unittest.main(verbosity=2)
