#!/usr/bin/env python3
"""
JARVIS Orchestrator 2.0 - Unified AI System
Combines:
- Semantic Cache for fast responses
- Department Agents for task execution
- Voice Pipeline for audio I/O
- Multi-model LLM routing

Run: python jarvis_orchestrator_v2.py
"""

import asyncio
import json
import os
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add local modules
sys.path.insert(0, os.path.dirname(__file__))

# Import our new modules
from jarvis_semantic_cache import SemanticCache, CacheWithPersistence
from department_agents_v2 import CEOAgent, TaskPriority
from voice_pipeline.jarvis_voice_v2 import VoicePipeline


@dataclass
class UserSession:
    """User session with context"""

    id: str
    created_at: float
    last_active: float
    message_count: int = 0
    preferences: Dict = field(default_factory=dict)
    context: Dict = field(default_factory=dict)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""

    # Cache settings
    cache_enabled: bool = True
    cache_similarity: float = 0.85
    cache_ttl: float = 3600.0

    # Voice settings
    voice_enabled: bool = False
    voice_hotkey: str = "ctrl+shift+v"

    # Agent settings
    agents_enabled: bool = True
    auto_route_tasks: bool = True

    # LLM settings
    default_model: str = "qwen2.5:14b"
    fallback_models: List[str] = field(
        default_factory=lambda: ["llama3.1:8b", "mistral:7b"]
    )

    # Response settings
    max_response_length: int = 2000
    include_sources: bool = True


class JARVISOrchestrator:
    """
    Unified JARVIS orchestrator combining all components:
    - Semantic Cache for fast repeated responses
    - Department Agents for task management
    - Voice Pipeline for audio interaction
    - Session management for context
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()

        # Initialize components
        print("Initializing JARVIS Orchestrator...")

        # Semantic cache
        if self.config.cache_enabled:
            self.cache = CacheWithPersistence(
                similarity_threshold=self.config.cache_similarity,
                default_ttl=self.config.cache_ttl,
                max_entries=500,
            )
            print("  ✅ Semantic Cache initialized")
        else:
            self.cache = None

        # Department agents
        if self.config.agents_enabled:
            self.ceo = CEOAgent()
            print("  ✅ Department Agents initialized")
        else:
            self.ceo = None

        # Voice pipeline (lazy load)
        self._voice_pipeline = None

        # Session management
        self.sessions: Dict[str, UserSession] = {}
        self.active_session: Optional[UserSession] = None
        self.session_history: deque = deque(maxlen=100)

        # LLM configuration
        self.ollama_base = os.getenv("OLLAMA_BASE", "http://localhost:11434")
        self.default_model = self.config.default_model

        print("  ✅ JARVIS Orchestrator ready\n")

    @property
    def voice_pipeline(self) -> Optional[VoicePipeline]:
        """Lazy load voice pipeline"""
        if self._voice_pipeline is None and self.config.voice_enabled:
            try:
                self._voice_pipeline = VoicePipeline()
            except Exception as e:
                print(f"Warning: Could not initialize voice: {e}")
        return self._voice_pipeline

    async def chat(
        self, message: str, session_id: str = None, context: Dict = None
    ) -> Dict[str, Any]:
        """
        Main chat entry point - processes message through all components
        """
        # Get or create session
        session = self._get_or_create_session(session_id)
        self.active_session = session
        session.message_count += 1
        session.last_active = datetime.now().timestamp()

        # Update context
        if context:
            session.context.update(context)

        response = {
            "session_id": session.id,
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "response": "",
            "sources": [],
            "tools_used": [],
            "cache_hit": False,
        }

        # Step 1: Check semantic cache
        if self.cache:
            cached = self.cache.get(message)
            if cached:
                response["response"] = cached
                response["cache_hit"] = True
                response["sources"].append("cache")
                print(f"📦 Cache hit for: {message[:30]}...")
                return response

        # Step 2: Check if this is a task for agents
        if self._is_task_request(message) and self.ceo:
            task_result = await self._process_task(message, session)
            response["response"] = task_result.get("result", "")
            response["tools_used"].append("department_agent")
            return response

        # Step 3: Generate LLM response
        llm_response = await self._generate_response(message, session)
        response["response"] = llm_response
        response["tools_used"].append("llm")

        # Step 4: Cache the response
        if self.cache and llm_response:
            self.cache.set(message, llm_response)

        return response

    def _is_task_request(self, message: str) -> bool:
        """Check if message is a task request"""
        task_keywords = [
            "create",
            "write",
            "analyze",
            "research",
            "schedule",
            "help me",
            "build",
            "make",
            "generate",
            "find",
        ]
        return any(kw in message.lower() for kw in task_keywords)

    async def _process_task(self, message: str, session: UserSession) -> Dict:
        """Process task through department agents"""
        # Determine priority
        priority = 3
        if "urgent" in message.lower() or "asap" in message.lower():
            priority = 1
        elif "important" in message.lower():
            priority = 2

        # Add task
        task_id = self.ceo.add_task(
            {"title": message[:50], "description": message, "priority": priority}
        )

        # Execute
        await self.ceo.run_until_complete(max_cycles=5)

        # Get result
        completed = self.ceo.completed_tasks
        if completed:
            last_task = completed[-1]
            return {
                "task_id": task_id,
                "result": last_task.result,
                "status": last_task.status.value,
            }

        return {"task_id": task_id, "result": "Task queued", "status": "pending"}

    async def _generate_response(self, message: str, session: UserSession) -> str:
        """Generate LLM response"""
        import httpx

        # Build context from session
        context_parts = []
        if session.context:
            for k, v in session.context.items():
                context_parts.append(f"{k}: {v}")

        system = f"""You are JARVIS, an advanced AI assistant.
You are helpful, intelligent, and slightly witty.
Keep responses concise but thorough.
Current session context: {" | ".join(context_parts)}"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base}/api/chat",
                    json={
                        "model": self.default_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": message},
                        ],
                        "stream": False,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "")[
                        : self.config.max_response_length
                    ]

        except Exception as e:
            return f"I encountered an issue: {str(e)[:100]}"

        return "I'm having trouble generating a response right now."

    def _get_or_create_session(self, session_id: str = None) -> UserSession:
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]

        # Create new session
        session = UserSession(
            id=session_id or f"session_{datetime.now().timestamp()}",
            created_at=datetime.now().timestamp(),
            last_active=datetime.now().timestamp(),
        )
        self.sessions[session.id] = session
        return session

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        stats = {
            "sessions": len(self.sessions),
            "active_session": self.active_session.id if self.active_session else None,
            "config": {
                "cache_enabled": self.config.cache_enabled,
                "agents_enabled": self.config.agents_enabled,
                "voice_enabled": self.config.voice_enabled,
            },
        }

        if self.cache:
            stats["cache"] = self.cache.get_stats()

        if self.ceo:
            stats["agents"] = self.ceo.get_status()

        return stats

    def invalidate_cache(self, pattern: str = None):
        """Invalidate cache"""
        if self.cache:
            self.cache.invalidate(pattern)
            print(
                f"🗑️ Cache invalidated" + (f" (pattern: {pattern})" if pattern else "")
            )

    def save_state(self):
        """Persist state to disk"""
        if self.cache:
            self.cache.save()
            print("💾 State saved")


class MCPIntegration:
    """Integration layer for MCP server"""

    def __init__(self, orchestrator: JARVISOrchestrator):
        self.orchestrator = orchestrator

    def get_tools(self) -> List[Dict]:
        """Get tools for MCP server"""
        return [
            {
                "name": "jarvis_chat",
                "description": "Chat with JARVIS AI assistant",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Your message"},
                        "session_id": {
                            "type": "string",
                            "description": "Optional session ID",
                        },
                        "context": {
                            "type": "object",
                            "description": "Optional context",
                        },
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "jarvis_create_task",
                "description": "Create a task for department agents",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Task title"},
                        "description": {
                            "type": "string",
                            "description": "Task description",
                        },
                        "priority": {"type": "integer", "description": "Priority 1-5"},
                        "department": {
                            "type": "string",
                            "description": "Department (content/research/support/operations)",
                        },
                    },
                    "required": ["title", "description"],
                },
            },
            {
                "name": "jarvis_get_stats",
                "description": "Get JARVIS system statistics",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "jarvis_invalidate_cache",
                "description": "Invalidate semantic cache",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Optional pattern to match",
                        }
                    },
                },
            },
        ]

    async def call_tool(self, name: str, arguments: Dict) -> Dict:
        """Call a tool"""
        if name == "jarvis_chat":
            result = await self.orchestrator.chat(
                message=arguments.get("message", ""),
                session_id=arguments.get("session_id"),
                context=arguments.get("context"),
            )
            return {
                "response": result["response"],
                "cache_hit": result.get("cache_hit", False),
            }

        elif name == "jarvis_create_task":
            if not self.orchestrator.ceo:
                return {"error": "Agents not enabled"}

            task_id = self.orchestrator.ceo.add_task(arguments)
            await self.orchestrator.ceo.run_until_complete()
            return {"task_id": task_id, "status": "created"}

        elif name == "jarvis_get_stats":
            return self.orchestrator.get_stats()

        elif name == "jarvis_invalidate_cache":
            self.orchestrator.invalidate_cache(arguments.get("pattern"))
            return {"status": "cleared"}

        return {"error": f"Unknown tool: {name}"}


async def demo():
    """Demo the orchestrator"""
    print("=" * 60)
    print("JARVIS Orchestrator 2.0 Demo")
    print("=" * 60)

    config = OrchestratorConfig(
        cache_enabled=True, agents_enabled=True, voice_enabled=False
    )

    orchestrator = JARVISOrchestrator(config)

    # Test chat
    print("\n1. Testing chat with cache...")
    response1 = await orchestrator.chat("What is AI?")
    print(f"   Response: {response1['response'][:80]}...")
    print(f"   Cache hit: {response1['cache_hit']}")

    # Second request should hit cache
    print("\n2. Testing cache hit...")
    response2 = await orchestrator.chat("What is AI?")
    print(f"   Cache hit: {response2['cache_hit']}")

    # Test task
    print("\n3. Testing task creation...")
    if orchestrator.ceo:
        task_id = orchestrator.ceo.add_task(
            {
                "title": "Research AI trends",
                "description": "Research current AI trends for 2025",
                "priority": 2,
                "department": "research",
            }
        )
        print(f"   Task created: {task_id}")

    # Get stats
    print("\n4. System statistics:")
    stats = orchestrator.get_stats()
    print(f"   Sessions: {stats['sessions']}")
    if "cache" in stats:
        print(f"   Cache hit rate: {stats['cache'].get('hit_rate_percent', 0)}%")

    # Save state
    print("\n5. Saving state...")
    orchestrator.save_state()

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import subprocess

    try:
        import httpx
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "httpx", "numpy"])
        import httpx
        import numpy as np

    asyncio.run(demo())
