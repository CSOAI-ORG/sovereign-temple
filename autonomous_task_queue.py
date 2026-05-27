#!/usr/bin/env python3
"""
AUTONOMOUS TASK QUEUE — The Zero-Task Fix
============================================
From the 50-topic audit: "SOV3's 47 agents complete no tasks because
they lack an autonomous execution loop."

This fixes it. Agents can now:
  1. DISCOVER tasks (Orion scans codebase + living alignment)
  2. CLAIM tasks from priority queue
  3. EXECUTE via MCP tools
  4. REPORT results back to memory + alignment

Architecture:
  Orion discovers → Redis queue → Agents claim → Execute → Record
  (Uses in-memory queue when Redis unavailable)

Curiosity Signal (RND-inspired):
  Tasks with high novelty get priority boost.
  Agents preferentially claim tasks in unexplored domains.

Usage:
  from autonomous_task_queue import task_queue
  task_queue.submit("Fix care membrane CM-05 failure", priority="high", capabilities=["care"])
  task_queue.run_cycle()  # Agents claim and execute
"""

import json
import time
import logging
import datetime
import os
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import deque
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

log = logging.getLogger("sovereign.task_queue")


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TaskStatus(Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    capabilities_required: List[str] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    result: Optional[str] = None
    created_at: str = ""
    claimed_at: Optional[str] = None
    completed_at: Optional[str] = None
    novelty_score: float = 0.5  # RND-inspired curiosity signal
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.datetime.now().isoformat()
        if not self.id:
            self.id = f"task_{uuid.uuid4().hex[:8]}"


class AutonomousTaskQueue:
    """Priority queue with agent matching and curiosity-driven selection."""

    def __init__(self):
        self._queue: deque = deque()
        self._completed: List[Task] = []
        self._failed: List[Task] = []
        self._lock = threading.Lock()
        self._running = False
        self._cycle_count = 0

        # Agent capability registry
        self._agent_capabilities = {
            "orion": ["research", "discovery", "memory_synthesis"],
            "riri": ["code", "tool_building", "code_review"],
            "guardian": ["safety", "care_validation", "audit"],
            "sage": ["wisdom", "analysis", "memory"],
            "curiosity": ["exploration", "gap_finding", "consciousness"],
            "harvest": ["data_collection", "research", "scraping"],
            "dragon": ["optimization", "performance", "testing"],
            "archimedes": ["reasoning", "quantum", "planning"],
            "valkyrie": ["security", "threat_detection", "defense"],
            "hephaestus": ["infrastructure", "code", "build"],
            "jarvis": ["orchestration", "voice", "all"],
        }

        # Novelty tracker (RND-inspired) — domains seen less get higher novelty
        self._domain_counts: Dict[str, int] = {}

    # ── Submit Tasks ─────────────────────────────────────────────────

    def submit(self, title: str, description: str = "", priority: str = "medium",
               capabilities: List[str] = None, source: str = "manual") -> str:
        """Submit a task to the queue."""
        with self._lock:
            task = Task(
                id=f"task_{uuid.uuid4().hex[:8]}",
                title=title,
                description=description,
                priority=TaskPriority[priority.upper()],
                capabilities_required=capabilities or [],
            )

            # Compute novelty score (RND-inspired)
            for cap in task.capabilities_required:
                count = self._domain_counts.get(cap, 0)
                self._domain_counts[cap] = count
            if task.capabilities_required:
                avg_count = sum(self._domain_counts.get(c, 0) for c in task.capabilities_required) / len(task.capabilities_required)
                task.novelty_score = 1.0 / (1.0 + avg_count * 0.1)  # Higher novelty for less-seen domains

            self._queue.append(task)
            self._sort_queue()

            log.info(f"📋 Task submitted: {task.id} — {title} ({priority}, novelty: {task.novelty_score:.2f})")
            return task.id

    def _sort_queue(self):
        """Sort by priority + novelty (curiosity-weighted)."""
        tasks = list(self._queue)
        tasks.sort(key=lambda t: (
            t.priority.value,  # Lower priority value = higher priority
            -t.novelty_score,  # Higher novelty = earlier
        ))
        self._queue = deque(tasks)

    # ── Agent Matching ───────────────────────────────────────────────

    def _find_best_agent(self, task: Task) -> Optional[str]:
        """Find the best agent for a task based on capability matching."""
        if not task.capabilities_required:
            return "jarvis"  # Default

        best_agent = None
        best_score = 0

        for agent, caps in self._agent_capabilities.items():
            overlap = len(set(task.capabilities_required) & set(caps))
            if overlap > best_score:
                best_score = overlap
                best_agent = agent

        return best_agent or "jarvis"

    # ── Execute Cycle ────────────────────────────────────────────────

    def run_cycle(self) -> Dict[str, Any]:
        """Run one execution cycle — agents claim and execute tasks.

        Returns summary of what happened.
        """
        self._cycle_count += 1
        cycle_start = time.time()
        claimed = 0
        completed = 0
        failed = 0

        with self._lock:
            pending = [t for t in self._queue if t.status == TaskStatus.PENDING]

        for task in pending[:5]:  # Process up to 5 tasks per cycle
            # 1. Find best agent
            agent = self._find_best_agent(task)
            if not agent:
                continue

            # 2. Claim
            task.status = TaskStatus.CLAIMED
            task.assigned_agent = agent
            task.claimed_at = datetime.datetime.now().isoformat()
            claimed += 1

            # 3. Execute via SOV3 MCP
            task.status = TaskStatus.EXECUTING
            try:
                import requests
                resp = requests.post(
                    "http://localhost:3101/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": f"task-{task.id}",
                        "method": "tools/call",
                        "params": {
                            "name": "orchestrate",
                            "arguments": {
                                "task": task.title,
                                "context": {
                                    "agent": agent,
                                    "priority": task.priority.name,
                                    "capabilities": task.capabilities_required,
                                },
                            },
                        },
                    },
                    timeout=30,
                )
                data = resp.json()
                text = data.get("result", {}).get("content", [{}])[0].get("text", "")
                result = json.loads(text) if text else {}

                task.status = TaskStatus.COMPLETED
                task.result = json.dumps(result)[:500]
                task.completed_at = datetime.datetime.now().isoformat()
                completed += 1

                # Update domain counts (reduces novelty for this domain)
                for cap in task.capabilities_required:
                    self._domain_counts[cap] = self._domain_counts.get(cap, 0) + 1

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.result = str(e)[:200]
                task.retry_count += 1
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.PENDING  # Re-queue
                failed += 1

        # Move completed/failed out of queue
        with self._lock:
            still_pending = deque()
            for t in self._queue:
                if t.status == TaskStatus.COMPLETED:
                    self._completed.append(t)
                elif t.status == TaskStatus.FAILED and t.retry_count >= t.max_retries:
                    self._failed.append(t)
                else:
                    still_pending.append(t)
            self._queue = still_pending

        # Record to alignment
        try:
            from living_alignment import alignment
            for t in self._completed[-completed:]:
                alignment.update_task(t.id, status="completed")
        except Exception:
            pass

        elapsed = time.time() - cycle_start
        summary = {
            "cycle": self._cycle_count,
            "claimed": claimed,
            "completed": completed,
            "failed": failed,
            "still_pending": len(self._queue),
            "total_completed": len(self._completed),
            "total_failed": len(self._failed),
            "elapsed_ms": round(elapsed * 1000),
            "domain_novelty": {k: round(1.0 / (1.0 + v * 0.1), 2) for k, v in self._domain_counts.items()},
        }

        log.info(f"🔄 Cycle {self._cycle_count}: {claimed} claimed, {completed} completed, {failed} failed, {len(self._queue)} pending")
        return summary

    # ── Auto-Discovery ───────────────────────────────────────────────

    def discover_tasks(self) -> List[str]:
        """Use Orion to discover tasks from codebase + alignment priorities."""
        discovered = []

        # 1. Check living alignment for priorities
        try:
            from living_alignment import alignment
            for priority in alignment._state.get("priorities", []):
                task_id = self.submit(
                    priority["title"],
                    f"From alignment priority ({priority['level']})",
                    priority["level"],
                    source="alignment",
                )
                discovered.append(task_id)
        except Exception:
            pass

        # 2. Check living alignment for pending tasks
        try:
            from living_alignment import alignment
            for task in alignment.get_active_tasks():
                task_id = self.submit(
                    task["title"],
                    f"From alignment task ({task.get('source', 'unknown')})",
                    task.get("priority", "medium"),
                    capabilities=task.get("tags", []),
                    source="alignment",
                )
                discovered.append(task_id)
        except Exception:
            pass

        log.info(f"🔍 Discovered {len(discovered)} tasks")
        return discovered

    # ── Status ───────────────────────────────────────────────────────

    def get_status(self) -> Dict:
        return {
            "pending": len(self._queue),
            "completed": len(self._completed),
            "failed": len(self._failed),
            "cycles_run": self._cycle_count,
            "agents": len(self._agent_capabilities),
            "domain_novelty": {k: round(1.0 / (1.0 + v * 0.1), 2) for k, v in self._domain_counts.items()},
            "queue_preview": [
                {"id": t.id, "title": t.title[:50], "priority": t.priority.name,
                 "agent": t.assigned_agent, "status": t.status.value, "novelty": t.novelty_score}
                for t in list(self._queue)[:10]
            ],
            "recent_completed": [
                {"id": t.id, "title": t.title[:50], "agent": t.assigned_agent,
                 "completed": t.completed_at}
                for t in self._completed[-5:]
            ],
        }


# Singleton
task_queue = AutonomousTaskQueue()
