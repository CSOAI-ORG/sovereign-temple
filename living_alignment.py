#!/usr/bin/env python3
"""
SOVEREIGN LIVING ALIGNMENT SYSTEM
===================================
A shared, real-time state that ALL agents, LLMs, and neural nets sync to.
Every component reads from and writes to this living document.

This is the "single source of truth" for the entire sovereign ecosystem:
  - Current priorities and tasks
  - Active beliefs and hypotheses
  - System health and capabilities
  - Learning progress and model status
  - Agent assignments and availability

Updated by:
  - Heartbeat (every pulse)
  - Jarvis (every interaction)
  - SOV3 consciousness (every state transition)
  - Neural nets (every training cycle)
  - Research sweeps (every finding)

Read by:
  - All LLM system prompts (context injection)
  - Agent task delegation
  - Heartbeat scheduling
  - Dashboard UIs

Usage:
  from living_alignment import alignment
  alignment.update_priority("Ship ARIA grant application", "critical", "2026-04-14")
  alignment.get_context()  # Returns formatted context for LLM injection
  alignment.sync()  # Persist to disk + SOV3 memory
"""

import json
import time
import datetime
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock

log = logging.getLogger("alignment")

ALIGNMENT_FILE = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "living_alignment.json"
ALIGNMENT_FILE.parent.mkdir(parents=True, exist_ok=True)


class LivingAlignment:
    """Shared real-time state for the sovereign ecosystem."""

    def __init__(self):
        self._lock = Lock()
        self._state = self._load()

    def _default_state(self) -> Dict:
        return {
            "last_updated": datetime.datetime.now().isoformat(),
            "version": 1,

            # ── Priorities (what matters right now) ──
            "priorities": [],

            # ── Active tasks (living todo list) ──
            "tasks": [],

            # ── Beliefs (what we currently believe to be true) ──
            "beliefs": [],

            # ── System capabilities (what's online and working) ──
            "capabilities": {
                "llm_providers": {},
                "neural_models": {},
                "services": {},
                "agents": {},
            },

            # ── Learning progress ──
            "learning": {
                "total_interactions": 0,
                "total_training_runs": 0,
                "last_training": None,
                "model_scores": {},
            },

            # ── Agent assignments ──
            "agent_assignments": {},

            # ── Consciousness state ──
            "consciousness": {
                "mode": "waking",
                "level": 0.0,
                "emotion": "neutral",
                "care_intensity": 0.0,
            },
        }

    # ── Priority Management ──────────────────────────────────────────

    def update_priority(self, title: str, level: str = "medium", deadline: str = None):
        """Add or update a priority."""
        with self._lock:
            # Remove existing with same title
            self._state["priorities"] = [
                p for p in self._state["priorities"] if p["title"] != title
            ]
            self._state["priorities"].append({
                "title": title,
                "level": level,  # critical, high, medium, low
                "deadline": deadline,
                "added": datetime.datetime.now().isoformat(),
            })
            # Sort by level
            level_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            self._state["priorities"].sort(key=lambda p: level_order.get(p["level"], 99))
            self._save()

    def remove_priority(self, title: str):
        with self._lock:
            self._state["priorities"] = [
                p for p in self._state["priorities"] if p["title"] != title
            ]
            self._save()

    # ── Task Management (living todo) ────────────────────────────────

    def add_task(self, title: str, assignee: str = "unassigned", priority: str = "medium",
                 source: str = "manual", tags: List[str] = None):
        """Add a task to the living todo list."""
        with self._lock:
            task_id = f"task_{int(time.time())}_{len(self._state['tasks'])}"
            self._state["tasks"].append({
                "id": task_id,
                "title": title,
                "assignee": assignee,
                "priority": priority,
                "status": "pending",
                "source": source,
                "tags": tags or [],
                "created": datetime.datetime.now().isoformat(),
            })
            self._save()
            return task_id

    def update_task(self, task_id: str, status: str = None, assignee: str = None):
        with self._lock:
            for task in self._state["tasks"]:
                if task["id"] == task_id:
                    if status:
                        task["status"] = status
                    if assignee:
                        task["assignee"] = assignee
                    task["updated"] = datetime.datetime.now().isoformat()
                    break
            self._save()

    def get_active_tasks(self) -> List[Dict]:
        return [t for t in self._state["tasks"] if t["status"] in ("pending", "in_progress")]

    # ── Belief Management ────────────────────────────────────────────

    def update_belief(self, belief: str, confidence: float, evidence: str = "",
                      domain: str = "general"):
        """Update a belief — replaces existing belief with same text."""
        with self._lock:
            self._state["beliefs"] = [
                b for b in self._state["beliefs"] if b["belief"] != belief
            ]
            self._state["beliefs"].append({
                "belief": belief,
                "confidence": confidence,
                "evidence": evidence[:300],
                "domain": domain,
                "updated": datetime.datetime.now().isoformat(),
            })
            # Keep top 50 beliefs by confidence
            self._state["beliefs"].sort(key=lambda b: b["confidence"], reverse=True)
            self._state["beliefs"] = self._state["beliefs"][:50]
            self._save()

    # ── Capability Tracking ──────────────────────────────────────────

    def update_capabilities(self, category: str, name: str, status: Dict):
        """Update a system capability status."""
        with self._lock:
            if category not in self._state["capabilities"]:
                self._state["capabilities"][category] = {}
            self._state["capabilities"][category][name] = {
                **status,
                "last_checked": datetime.datetime.now().isoformat(),
            }
            self._save()

    # ── Consciousness Sync ───────────────────────────────────────────

    def sync_consciousness(self, mode: str, level: float, emotion: str, care: float):
        with self._lock:
            self._state["consciousness"] = {
                "mode": mode,
                "level": level,
                "emotion": emotion,
                "care_intensity": care,
                "synced_at": datetime.datetime.now().isoformat(),
            }
            self._save()

    # ── Learning Progress ────────────────────────────────────────────

    def record_training(self, model_name: str, metrics: Dict):
        with self._lock:
            self._state["learning"]["total_training_runs"] += 1
            self._state["learning"]["last_training"] = datetime.datetime.now().isoformat()
            self._state["learning"]["model_scores"][model_name] = {
                "metrics": metrics,
                "trained_at": datetime.datetime.now().isoformat(),
            }
            self._save()

    def increment_interactions(self):
        with self._lock:
            self._state["learning"]["total_interactions"] += 1

    # ── Context Generation (for LLM injection) ──────────────────────

    def get_context(self, max_tokens: int = 500) -> str:
        """Generate a formatted context string for LLM system prompts."""
        now = datetime.datetime.now()
        lines = [f"[SOVEREIGN ALIGNMENT — {now.strftime('%H:%M %Z, %A %B %d')}]"]

        # Priorities
        priorities = self._state.get("priorities", [])[:5]
        if priorities:
            lines.append("\nPRIORITIES:")
            for p in priorities:
                deadline = f" (due {p['deadline']})" if p.get("deadline") else ""
                lines.append(f"  [{p['level'].upper()}] {p['title']}{deadline}")

        # Active tasks
        active = self.get_active_tasks()[:5]
        if active:
            lines.append(f"\nACTIVE TASKS ({len(active)}):")
            for t in active:
                lines.append(f"  - {t['title']} [{t['assignee']}] ({t['status']})")

        # Consciousness
        c = self._state.get("consciousness", {})
        if c.get("level"):
            lines.append(f"\nCONSCIOUSNESS: {c.get('mode', '?')} | {c.get('level', 0):.0%} | {c.get('emotion', '?')}")

        # Learning
        learn = self._state.get("learning", {})
        if learn.get("total_interactions"):
            lines.append(f"\nLEARNING: {learn['total_interactions']} interactions, {learn['total_training_runs']} training runs")

        # Top beliefs
        beliefs = self._state.get("beliefs", [])[:3]
        if beliefs:
            lines.append("\nCURRENT BELIEFS:")
            for b in beliefs:
                lines.append(f"  ({b['confidence']:.0%}) {b['belief']}")

        result = "\n".join(lines)
        # Rough token limit (4 chars ≈ 1 token)
        if len(result) > max_tokens * 4:
            result = result[:max_tokens * 4] + "\n  ...(truncated)"
        return result

    # ── Persistence ──────────────────────────────────────────────────

    def _load(self) -> Dict:
        try:
            with open(ALIGNMENT_FILE) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._default_state()

    def _save(self):
        self._state["last_updated"] = datetime.datetime.now().isoformat()
        with open(ALIGNMENT_FILE, "w") as f:
            json.dump(self._state, f, indent=2)

    def sync_to_sov3(self):
        """Push alignment state to SOV3 memory for cross-system access."""
        try:
            import requests
            requests.post(
                "http://localhost:3101/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "alignment-sync",
                    "method": "tools/call",
                    "params": {
                        "name": "record_memory",
                        "arguments": {
                            "content": f"[ALIGNMENT SYNC] {self.get_context(300)}",
                            "source_agent": "alignment_system",
                            "memory_type": "alignment",
                            "tags": ["alignment", "priorities", "tasks", time.strftime("%Y-%m-%d")],
                            "importance": 0.9,
                        },
                    },
                },
                timeout=5,
            )
        except Exception:
            pass

    def get_full_state(self) -> Dict:
        return self._state.copy()


# Singleton
alignment = LivingAlignment()
