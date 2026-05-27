#!/usr/bin/env python3
"""
Research Dashboard - See what's happening in real-time
Shows simulation progress, model thinking, data analysis
"""

import time
import threading
import json
from typing import Dict, List, Optional
from collections import deque


class ResearchDashboard:
    """
    Real-time research visualization
    Shows: active simulations, model thinking, data, outcomes
    """

    def __init__(self):
        self.sessions = {}
        self.active_tasks = deque(maxlen=50)
        self.model_thinking = {}  # What's each model processing
        self.simulations = {}  # Running simulations
        self.results = deque(maxlen=100)
        self.observations = deque(maxlen=50)
        self.max_sessions = 5

    def start_session(self, session_id: str, topic: str):
        """Start a new research session"""
        self.sessions[session_id] = {
            "topic": topic,
            "started_at": time.time(),
            "status": "active",
            "progress": 0,
            "steps": [],
        }
        self._log(f"📡 Research session started: {topic}")

    def update_progress(self, session_id: str, progress: int, step: str):
        """Update session progress"""
        if session_id in self.sessions:
            self.sessions[session_id]["progress"] = progress
            self.sessions[session_id]["steps"].append(
                {
                    "step": step,
                    "at": time.time(),
                }
            )
            self._log(f"  📊 {progress}%: {step}")

    def add_model_thinking(self, model: str, thinking: str):
        """Log what a model is thinking"""
        self.model_thinking[model] = {
            "thinking": thinking[:500],
            "at": time.time(),
        }
        self.active_tasks.append(
            {
                "model": model,
                "action": "thinking",
                "detail": thinking[:100],
                "at": time.time(),
            }
        )

    def add_simulation(self, sim_id: str, name: str, params: Dict):
        """Add a running simulation"""
        self.simulations[sim_id] = {
            "name": name,
            "params": params,
            "started_at": time.time(),
            "status": "running",
        }
        self._log(f"🔬 Simulation started: {name}")

    def complete_simulation(self, sim_id: str, result: Dict):
        """Mark simulation complete"""
        if sim_id in self.simulations:
            self.simulations[sim_id]["status"] = "complete"
            self.simulations[sim_id]["result"] = result
            self.simulations[sim_id]["completed_at"] = time.time()
            self._log(f"✅ Simulation complete: {self.simulations[sim_id]['name']}")

    def add_observation(self, observation: str, category: str = "insight"):
        """Add an observation/finding"""
        obs = {
            "text": observation,
            "category": category,
            "at": time.time(),
        }
        self.observations.append(obs)
        self._log(f"💡 [{category.upper()}] {observation[:100]}")

    def add_result(self, result: Dict):
        """Add a result/outcome"""
        self.results.append(
            {
                "result": result,
                "at": time.time(),
            }
        )

    def _log(self, message: str):
        """Internal logging"""
        print(f"  📺 {message}")

    def get_status(self) -> str:
        """Get current status for display"""
        lines = []

        # Active sessions
        if self.sessions:
            lines.append("🔬 ACTIVE RESEARCH:")
            for sid, sess in self.sessions.items():
                if sess["status"] == "active":
                    lines.append(f"  • {sess['topic']} ({sess['progress']}%)")

        # Running simulations
        running = [s for s in self.simulations.values() if s["status"] == "running"]
        if running:
            lines.append("\n⚡ RUNNING SIMULATIONS:")
            for sim in running:
                elapsed = time.time() - sim["started_at"]
                lines.append(f"  • {sim['name']} ({elapsed:.1f}s)")

        # Recent observations
        if self.observations:
            lines.append("\n💡 LATEST INSIGHTS:")
            for obs in list(self.observations)[-3:]:
                lines.append(f"  • {obs['text'][:80]}...")

        return "\n".join(lines) if lines else "No active research"

    def clear(self):
        """Clear dashboard"""
        self.sessions.clear()
        self.simulations.clear()
        self.observations.clear()
        self.results.clear()
        self.model_thinking.clear()


# Global dashboard
_dashboard = None


def get_dashboard() -> ResearchDashboard:
    global _dashboard
    if _dashboard is None:
        _dashboard = ResearchDashboard()
    return _dashboard


# Context manager for research sessions
class ResearchContext:
    """Context manager for research"""

    def __init__(self, topic: str):
        self.topic = topic
        self.session_id = f"{hash(topic)}_{int(time.time())}"
        self.dashboard = get_dashboard()

    def __enter__(self):
        self.dashboard.start_session(self.session_id, self.topic)
        return self

    def __exit__(self, *args):
        self.dashboard.update_progress(self.session_id, 100, "Complete")

    def progress(self, percent: int, step: str):
        self.dashboard.update_progress(self.session_id, percent, step)

    def observe(self, text: str, category: str = "insight"):
        self.dashboard.add_observation(text, category)

    def think(self, model: str, thought: str):
        self.dashboard.add_model_thinking(model, thought)


if __name__ == "__main__":
    dashboard = get_dashboard()

    # Test
    with ResearchContext("Consciousness research") as ctx:
        ctx.progress(10, "Initializing models")
        ctx.think("Gemma 4", "Analyzing substrate independence theory...")
        ctx.progress(30, "Running substrate simulations")
        ctx.observe("Substrate independence may be related to quantum coherence")
        ctx.progress(60, "Analyzing historical data")
        ctx.observe("Found correlation with alchemical texts")
        ctx.progress(90, "Compiling results")

    print("\n" + "=" * 50)
    print(dashboard.get_status())
