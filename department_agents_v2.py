#!/usr/bin/env python3
"""
MEOK Department Agents 2.0 - LLM-Powered Autonomous Agents
Features:
- Real LLM integration (Ollama)
- Task prioritization and execution
- Inter-department communication
- Progress tracking and reporting

Run: python department_agents_v2.py
"""

import asyncio
import json
import logging
import os
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncIterator, Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod

try:
    import httpx
except ImportError:
    httpx = None

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s"
)
log = logging.getLogger("dept-agents-v2")


class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Task with full metadata"""

    id: str
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    assigned_to: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentCapability:
    """Agent skill capability"""

    name: str
    description: str
    examples: List[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Base class for all agents"""

    def __init__(self, name: str, role: str, capabilities: List[AgentCapability]):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.tasks: List[Task] = []
        self.task_history: deque = deque(maxlen=50)
        self.active = False
        self.current_task: Optional[Task] = None

    @abstractmethod
    async def process_task(self, task: Task) -> Any:
        """Process a task - must be implemented by subclass"""
        pass

    @abstractmethod
    async def generate_response(self, prompt: str, context: Dict = None) -> str:
        """Generate LLM response"""
        pass

    def add_task(self, task: Task):
        """Add task to queue"""
        self.tasks.append(task)
        self.tasks.sort(key=lambda t: t.priority.value)
        log.info(f"📋 [{self.name}] Task added: {task.title}")

    async def execute_next(self) -> Optional[Task]:
        """Execute next available task"""
        # Find task with no pending dependencies
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                deps_met = all(
                    self._get_task_status(dep)
                    in (TaskStatus.COMPLETED, TaskStatus.CANCELLED)
                    for dep in task.dependencies
                )
                if deps_met:
                    return await self._run_task(task)
        return None

    def _get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of dependent task"""
        for t in self.tasks:
            if t.id == task_id:
                return t.status
        return TaskStatus.COMPLETED  # Assume completed if not found

    async def _run_task(self, task: Task) -> Task:
        """Run a single task"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        self.current_task = task
        self.active = True

        log.info(f"⚙️  [{self.name}] Executing: {task.title}")

        try:
            result = await self.process_task(task)
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            log.info(f"✅ [{self.name}] Completed: {task.title}")
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            log.error(f"❌ [{self.name}] Failed: {task.title} - {e}")

        self.task_history.append(task)
        self.current_task = None
        if not self.tasks:
            self.active = False

        return task

    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "active": self.active,
            "tasks_pending": sum(
                1 for t in self.tasks if t.status == TaskStatus.PENDING
            ),
            "tasks_running": sum(
                1 for t in self.tasks if t.status == TaskStatus.RUNNING
            ),
            "tasks_completed": sum(
                1 for t in self.tasks if t.status == TaskStatus.COMPLETED
            ),
            "current_task": self.current_task.title if self.current_task else None,
        }


class OllamaClient:
    """Async Ollama client for LLM calls"""

    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:14b"
    ):
        self.base_url = base_url
        self.model = model
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if not self.client:
            self.client = httpx.AsyncClient(timeout=60.0)
        return self.client

    async def chat(
        self, messages: List[Dict[str, str]], temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """Stream chat completion"""
        client = await self._get_client()

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }

        try:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"].get("content", "")
                                if content:
                                    yield content
                            if data.get("done", False):
                                break
                        except:
                            pass
        except Exception as e:
            log.error(f"Ollama error: {e}")
            yield f"[Error: {e}]"

    async def complete(
        self, prompt: str, system: str = None, temperature: float = 0.7
    ) -> str:
        """Single completion"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        full_text = ""
        async for chunk in self.chat(messages, temperature):
            full_text += chunk

        return full_text


class ContentAgent(BaseAgent):
    """Content Department Agent"""

    def __init__(self, llm: OllamaClient):
        super().__init__(
            name="ContentAgent",
            role="Content Creation & Marketing",
            capabilities=[
                AgentCapability("write", "Write content", ["blog posts", "emails"]),
                AgentCapability("summarize", "Summarize text", ["long documents"]),
                AgentCapability("brainstorm", "Generate ideas", ["campaign ideas"]),
            ],
        )
        self.llm = llm

    async def generate_response(self, prompt: str, context: Dict = None) -> str:
        system = """You are a creative content specialist. 
Create engaging, clear, and valuable content. Be concise but thorough."""
        return await self.llm.complete(prompt, system)

    async def process_task(self, task: Task) -> Any:
        if "write" in task.title.lower():
            return await self._write_content(task)
        elif "summarize" in task.title.lower():
            return await self._summarize(task)
        elif "brainstorm" in task.title.lower():
            return await self._brainstorm(task)
        else:
            return await self.generate_response(task.description)

    async def _write_content(self, task: Task) -> str:
        prompt = f"Write content for: {task.description}"
        return await self.generate_response(prompt)

    async def _summarize(self, task: Task) -> str:
        text = task.metadata.get("text", "")
        prompt = f"Summarize this text:\n\n{text[:2000]}"
        return await self.generate_response(prompt)

    async def _brainstorm(self, task: Task) -> str:
        prompt = f"Brainstorm ideas for: {task.description}"
        return await self.generate_response(prompt)


class ResearchAgent(BaseAgent):
    """Research Department Agent"""

    def __init__(self, llm: OllamaClient):
        super().__init__(
            name="ResearchAgent",
            role="Research & Analysis",
            capabilities=[
                AgentCapability("analyze", "Analyze data", ["trends", "patterns"]),
                AgentCapability(
                    "compare", "Compare options", ["products", "solutions"]
                ),
                AgentCapability("report", "Create reports", ["findings", "summaries"]),
            ],
        )
        self.llm = llm

    async def generate_response(self, prompt: str, context: Dict = None) -> str:
        system = """You are a research analyst. 
Be thorough, data-driven, and objective. Provide well-reasoned analysis."""
        return await self.llm.complete(prompt, system)

    async def process_task(self, task: Task) -> Any:
        if "analyze" in task.title.lower():
            return await self._analyze(task)
        elif "compare" in task.title.lower():
            return await self._compare(task)
        elif "report" in task.title.lower():
            return await self._report(task)
        else:
            return await self.generate_response(task.description)

    async def _analyze(self, task: Task) -> str:
        prompt = f"Analyze: {task.description}"
        return await self.generate_response(prompt)

    async def _compare(self, task: Task) -> str:
        items = task.metadata.get("items", [])
        prompt = f"Compare: {', '.join(items)}"
        return await self.generate_response(prompt)

    async def _report(self, task: Task) -> str:
        prompt = f"Create a report on: {task.description}"
        return await self.generate_response(prompt)


class SupportAgent(BaseAgent):
    """Support Department Agent"""

    def __init__(self, llm: OllamaClient):
        super().__init__(
            name="SupportAgent",
            role="Customer Support",
            capabilities=[
                AgentCapability(
                    "answer", "Answer questions", ["FAQ", "troubleshooting"]
                ),
                AgentCapability("escalate", "Escalate issues", ["critical", "complex"]),
                AgentCapability(
                    "triage", "Categorize issues", ["priority", "department"]
                ),
            ],
        )
        self.llm = llm

    async def generate_response(self, prompt: str, context: Dict = None) -> str:
        system = """You are a helpful support agent.
Be empathetic, clear, and solution-oriented. Always try to help first."""
        return await self.llm.complete(prompt, system)

    async def process_task(self, task: Task) -> Any:
        if "answer" in task.title.lower():
            return await self._answer_question(task)
        elif "escalate" in task.title.lower():
            return await self._escalate(task)
        elif "triage" in task.title.lower():
            return await self._triage(task)
        else:
            return await self.generate_response(task.description)

    async def _answer_question(self, task: Task) -> str:
        prompt = f"Answer this question: {task.description}"
        return await self.generate_response(prompt)

    async def _escalate(self, task: Task) -> Dict:
        return {
            "escalated": True,
            "reason": task.metadata.get("reason", "Complex issue"),
            "priority": task.priority.name,
        }

    async def _triage(self, task: Task) -> Dict:
        return {
            "category": "general",
            "priority": task.priority.name,
            "estimated_response_time": "1 hour",
        }


class OperationsAgent(BaseAgent):
    """Operations Department Agent"""

    def __init__(self, llm: OllamaClient):
        super().__init__(
            name="OperationsAgent",
            role="Operations & Scheduling",
            capabilities=[
                AgentCapability(
                    "schedule", "Schedule tasks", ["meetings", "reminders"]
                ),
                AgentCapability(
                    "coordinate", "Coordinate resources", ["teams", "tools"]
                ),
                AgentCapability(
                    "optimize", "Optimize workflows", ["processes", "efficiency"]
                ),
            ],
        )
        self.llm = llm

    async def generate_response(self, prompt: str, context: Dict = None) -> str:
        system = """You are an operations specialist.
Be practical, organized, and efficient. Focus on getting things done."""
        return await self.llm.complete(prompt, system)

    async def process_task(self, task: Task) -> Any:
        if "schedule" in task.title.lower():
            return await self._schedule(task)
        elif "coordinate" in task.title.lower():
            return await self._coordinate(task)
        elif "optimize" in task.title.lower():
            return await self._optimize(task)
        else:
            return await self.generate_response(task.description)

    async def _schedule(self, task: Task) -> Dict:
        return {
            "scheduled": True,
            "task": task.title,
            "timestamp": datetime.now().isoformat(),
        }

    async def _coordinate(self, task: Task) -> str:
        prompt = f"Coordinate: {task.description}"
        return await self.generate_response(prompt)

    async def _optimize(self, task: Task) -> str:
        prompt = f"Optimize this: {task.description}"
        return await self.generate_response(prompt)


class CEOAgent:
    """CEO Agent - Orchestrates all departments"""

    def __init__(self):
        self.llm = OllamaClient(model="qwen2.5:14b")

        # Initialize department agents
        self.agents = {
            "content": ContentAgent(self.llm),
            "research": ResearchAgent(self.llm),
            "support": SupportAgent(self.llm),
            "operations": OperationsAgent(self.llm),
        }

        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []

    def add_task(self, task: Dict) -> str:
        """Add a new task and route to appropriate department"""
        task_obj = Task(
            id=str(uuid.uuid4())[:8],
            title=task.get("title", "Untitled"),
            description=task.get("description", ""),
            priority=TaskPriority(task.get("priority", 3)),
            status=TaskStatus.PENDING,
            created_at=datetime.now().isoformat(),
            metadata=task.get("metadata", {}),
        )

        # Route to department
        department = task.get("department", self._route_task(task_obj))
        if department in self.agents:
            self.agents[department].add_task(task_obj)
        else:
            self.task_queue.append(task_obj)

        log.info(f"📨 Task {task_obj.id} routed to {department}")
        return task_obj.id

    def _route_task(self, task: Task) -> str:
        """Route task to appropriate department based on title/description"""
        text = (task.title + " " + task.description).lower()

        if any(w in text for w in ["content", "write", "blog", "social", "marketing"]):
            return "content"
        elif any(
            w in text for w in ["research", "analyze", "compare", "report", "data"]
        ):
            return "research"
        elif any(w in text for w in ["support", "help", "issue", "bug", "question"]):
            return "support"
        elif any(w in text for w in ["schedule", "coordina", "operat", "workflow"]):
            return "operations"

        return "research"  # Default

    async def run_cycle(self):
        """Run one execution cycle across all departments"""
        results = []

        for dept, agent in self.agents.items():
            if agent.tasks:
                result = await agent.execute_next()
                if result and result.status == TaskStatus.COMPLETED:
                    self.completed_tasks.append(result)
                    results.append(
                        {
                            "department": dept,
                            "task": result.title,
                            "status": result.status.value,
                            "result": str(result.result)[:100]
                            if result.result
                            else None,
                        }
                    )

        return results

    async def run_until_complete(self, max_cycles: int = 10):
        """Run until all tasks complete or max cycles reached"""
        for i in range(max_cycles):
            has_work = any(agent.tasks for agent in self.agents.values())
            if not has_work:
                break

            results = await self.run_cycle()
            if results:
                for r in results:
                    print(f"  ✅ {r['department']}: {r['task']}")

            await asyncio.sleep(0.5)

    def get_status(self) -> Dict:
        """Get overall system status"""
        return {
            "departments": {
                dept: agent.get_status() for dept, agent in self.agents.items()
            },
            "queued_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
        }


async def demo():
    """Demo the department agents"""
    print("=" * 50)
    print("MEOK Department Agents 2.0 Demo")
    print("=" * 50)

    ceo = CEOAgent()

    # Add some tasks
    print("\n1. Adding tasks...")

    ceo.add_task(
        {
            "title": "Write blog post",
            "description": "Write a blog post about AI assistants",
            "priority": 3,
            "department": "content",
        }
    )

    ceo.add_task(
        {
            "title": "Analyze market trends",
            "description": "Analyze current AI market trends for 2025",
            "priority": 2,
            "department": "research",
        }
    )

    ceo.add_task(
        {
            "title": "Answer user question",
            "description": "How do I reset my password?",
            "priority": 2,
            "department": "support",
        }
    )

    ceo.add_task(
        {
            "title": "Optimize workflow",
            "description": "Optimize the content creation workflow",
            "priority": 4,
            "department": "operations",
        }
    )

    print("   Added 4 tasks")

    # Show status
    print("\n2. Initial status:")
    status = ceo.get_status()
    for dept, info in status["departments"].items():
        print(f"   {dept}: {info['tasks_pending']} pending")

    # Run tasks
    print("\n3. Executing tasks...")
    await ceo.run_until_complete()

    # Final status
    print("\n4. Final status:")
    status = ceo.get_status()
    for dept, info in status["departments"].items():
        print(f"   {dept}: {info['tasks_completed']} completed")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    if httpx is None:
        print("Installing httpx...")
        import subprocess

        subprocess.run([__import__("sys").executable, "-m", "pip", "install", "httpx"])

    asyncio.run(demo())
