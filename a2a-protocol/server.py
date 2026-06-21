"""A2A Server — Expose MEOKCLAW as an A2A-compliant agent."""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, Optional, AsyncIterator

from .agent_card import AgentCard


class A2AServer:
    """A2A server implementation for MEOKCLAW.

    Endpoints:
    - GET /.well-known/agent.json → AgentCard
    - POST /a2a/v1/tasks → Create task
    - POST /a2a/v1/tasks/{id} → Get task status
    - POST /a2a/v1/tasks/{id}/cancel → Cancel task
    - POST /a2a/v1/tasks/{id}/message → Send message
    """

    def __init__(self, agent_card: AgentCard):
        self.agent_card = agent_card
        self._tasks: Dict[str, Dict] = {}
        self._handlers: Dict[str, callable] = {}

    def register_handler(self, skill_id: str, handler: callable):
        """Register a handler for a specific skill."""
        self._handlers[skill_id] = handler

    def get_agent_card(self) -> Dict:
        return self.agent_card.to_dict()

    async def create_task(self, task_request: Dict) -> Dict:
        """Create a new A2A task."""
        task_id = f"task_{len(self._tasks)}_{asyncio.get_event_loop().time()}"
        task = {
            "id": task_id,
            "status": "submitted",
            "messages": [task_request.get("message", {})],
            "artifacts": [],
            "history": [],
        }
        self._tasks[task_id] = task

        # Auto-execute if skill handler registered
        skill_id = task_request.get("skill", "chat")
        handler = self._handlers.get(skill_id)
        if handler:
            asyncio.create_task(self._execute_task(task_id, handler, task_request))

        return {"id": task_id, "status": "submitted"}

    async def _execute_task(self, task_id: str, handler: callable, request: Dict):
        """Execute task handler asynchronously."""
        try:
            self._tasks[task_id]["status"] = "working"
            result = await handler(request)
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["artifacts"].append({
                "type": "text",
                "content": result,
            })
        except Exception as e:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["error"] = str(e)

    def get_task(self, task_id: str) -> Optional[Dict]:
        return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "canceled"
            return True
        return False

    async def stream_task(self, task_id: str) -> AsyncIterator[str]:
        """Stream task updates via SSE."""
        task = self._tasks.get(task_id)
        if not task:
            yield json.dumps({"error": "Task not found"})
            return

        last_artifact_count = 0
        while task["status"] in ("submitted", "working"):
            current = len(task["artifacts"])
            if current > last_artifact_count:
                for artifact in task["artifacts"][last_artifact_count:]:
                    yield json.dumps({"artifact": artifact, "status": task["status"]})
                last_artifact_count = current
            await asyncio.sleep(0.1)

        yield json.dumps({"status": task["status"], "artifacts": task["artifacts"]})
