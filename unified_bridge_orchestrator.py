#!/usr/bin/env python3
"""
Unified Bridge Orchestrator - Central coordination for all bridges
Synthesizes: Memory, Tools, Computer Use, Browser, Calendar, Quantum Council
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskType(Enum):
    """Task classification for routing"""

    CONVERSATION = "conversation"
    REASONING = "reasoning"
    CODING = "coding"
    SEARCH = "search"
    MEMORY = "memory"
    COMPUTER = "computer"
    CALENDAR = "calendar"
    CREATIVE = "creative"
    MULTI = "multi"  # Multiple capabilities needed


@dataclass
class BridgeResponse:
    success: bool
    data: Any = None
    error: str = None
    timing_ms: float = 0
    source: str = ""


class UnifiedBridgeOrchestrator:
    """
    Central orchestrator for all bridge systems
    Routes tasks to appropriate bridges and synthesizes results
    """

    def __init__(self):
        self.bridges: Dict[str, Any] = {}
        self._initialize_bridges()

    def _initialize_bridges(self):
        """Initialize all available bridges"""
        print("🌐 Initializing Unified Bridge Network...")

        # Memory Bridge
        try:
            from sov3_memory_hub import get_memory_hub

            self.bridges["memory"] = get_memory_hub()
            print("  ✅ Memory Hub")
        except Exception as e:
            print(f"  ❌ Memory Hub: {e}")

        # Tool Bridge
        try:
            from sov3_tool_bridge import get_tool_bridge

            self.bridges["tools"] = get_tool_bridge()
            print("  ✅ Tool Bridge")
        except Exception as e:
            print(f"  ❌ Tool Bridge: {e}")

        # Computer Use
        try:
            from computer_use_bridge import get_computer_use

            self.bridges["computer"] = get_computer_use()
            print("  ✅ Computer Use")
        except Exception as e:
            print(f"  ❌ Computer Use: {e}")

        # Browser
        try:
            from browser_automation_bridge import get_simple_search

            self.bridges["browser"] = get_simple_search()
            print("  ✅ Browser")
        except Exception as e:
            print(f"  ❌ Browser: {e}")

        # Calendar
        try:
            from calendar_bridge import get_calendar_bridge

            self.bridges["calendar"] = get_calendar_bridge()
            print("  ✅ Calendar")
        except Exception as e:
            print(f"  ❌ Calendar: {e}")

        # Bridge Network
        try:
            from sov3_bridge_network import get_bridge_network

            self.bridges["network"] = get_bridge_network()
            print("  ✅ Bridge Network")
        except Exception as e:
            print(f"  ❌ Bridge Network: {e}")

        # Quantum Council
        try:
            from quantum_council import get_council

            self.bridges["council"] = get_council()
            print("  ✅ Quantum Council")
        except Exception as e:
            print(f"  ❌ Quantum Council: {e}")

        print(f"\n🌐 Unified Bridge Network: {len(self.bridges)} bridges active")

    def classify_task(self, prompt: str) -> TaskType:
        """Classify the type of task"""
        prompt_lower = prompt.lower()

        if any(
            k in prompt_lower
            for k in ["calendar", "event", "schedule", "meeting", "tomorrow", "today"]
        ):
            return TaskType.CALENDAR

        if any(
            k in prompt_lower
            for k in ["click", "type", "screenshot", "mouse", "desktop", "open app"]
        ):
            return TaskType.COMPUTER

        if any(
            k in prompt_lower for k in ["search", "web", "find", "look up", "google"]
        ):
            return TaskType.SEARCH

        if any(
            k in prompt_lower
            for k in ["remember", "memory", "recall", "past", "forget"]
        ):
            return TaskType.MEMORY

        if any(
            k in prompt_lower
            for k in ["code", "debug", "function", "program", "script"]
        ):
            return TaskType.CODING

        if any(
            k in prompt_lower
            for k in ["why", "how", "explain", "think", "analyze", "compare"]
        ):
            return TaskType.REASONING

        if any(
            k in prompt_lower for k in ["create", "write", "story", "poem", "creative"]
        ):
            return TaskType.CREATIVE

        if any(
            k in prompt_lower for k in ["council", "everyone", "all models", "debate"]
        ):
            return TaskType.MULTI

        return TaskType.CONVERSATION

    async def execute(self, prompt: str, context: Dict = None) -> BridgeResponse:
        """Execute a task by routing to appropriate bridge"""
        start_time = time.time()
        task_type = self.classify_task(prompt)

        print(f"🎯 Task classified as: {task_type.value}")

        try:
            if task_type == TaskType.CALENDAR:
                return await self._handle_calendar(prompt, start_time)

            elif task_type == TaskType.COMPUTER:
                return await self._handle_computer(prompt, start_time)

            elif task_type == TaskType.SEARCH:
                return await self._handle_search(prompt, start_time)

            elif task_type == TaskType.MEMORY:
                return await self._handle_memory(prompt, start_time)

            elif task_type == TaskType.CODING:
                return await self._handle_coding(prompt, start_time)

            elif task_type == TaskType.MULTI:
                return await self._handle_council(prompt, start_time)

            else:
                # Default - use LLM (handled elsewhere)
                return BridgeResponse(
                    success=False,
                    data=None,
                    timing_ms=(time.time() - start_time) * 1000,
                    source="orchestrator",
                )

        except Exception as e:
            return BridgeResponse(
                success=False,
                error=str(e),
                timing_ms=(time.time() - start_time) * 1000,
                source="orchestrator",
            )

    async def _handle_calendar(self, prompt: str, start_time: float) -> BridgeResponse:
        """Handle calendar-related tasks"""
        calendar = self.bridges.get("calendar")

        if not calendar:
            return BridgeResponse(success=False, error="Calendar bridge not available")

        try:
            result = await calendar.get_events(days_ahead=7)
            return BridgeResponse(
                success=True,
                data=result,
                timing_ms=(time.time() - start_time) * 1000,
                source="calendar_bridge",
            )
        except Exception as e:
            return BridgeResponse(success=False, error=str(e))

    async def _handle_computer(self, prompt: str, start_time: float) -> BridgeResponse:
        """Handle computer automation tasks"""
        computer = self.bridges.get("computer")

        if not computer:
            return BridgeResponse(
                success=False, error="Computer Use bridge not available"
            )

        prompt_lower = prompt.lower()

        # Route to appropriate computer action
        if "screenshot" in prompt_lower:
            result = computer.screenshot()
        elif "click" in prompt_lower:
            # Extract coordinates if provided
            result = {"action": "click", "note": "Use 'at X Y' for coordinates"}
        elif "type" in prompt_lower:
            result = {"action": "type", "note": "Specify text to type"}
        elif "open app" in prompt_lower or "open" in prompt_lower:
            # Try to extract app name
            result = computer.get_window_list()[:5]
        else:
            result = computer.get_screen_size()

        return BridgeResponse(
            success=True,
            data=result,
            timing_ms=(time.time() - start_time) * 1000,
            source="computer_use_bridge",
        )

    async def _handle_search(self, prompt: str, start_time: float) -> BridgeResponse:
        """Handle web search"""
        browser = self.bridges.get("browser")

        if not browser:
            return BridgeResponse(success=False, error="Browser bridge not available")

        # Extract search query
        search_terms = prompt.lower()
        for phrase in ["search for", "search", "find", "look up"]:
            if phrase in search_terms:
                query = prompt[prompt.lower().find(phrase) + len(phrase) :].strip()
                break
        else:
            query = prompt

        try:
            result = await browser.search(query, num_results=5)
            return BridgeResponse(
                success=True,
                data=result,
                timing_ms=(time.time() - start_time) * 1000,
                source="browser_bridge",
            )
        except Exception as e:
            return BridgeResponse(success=False, error=str(e))

    async def _handle_memory(self, prompt: str, start_time: float) -> BridgeResponse:
        """Handle memory tasks"""
        memory = self.bridges.get("memory")

        if not memory:
            return BridgeResponse(success=False, error="Memory bridge not available")

        prompt_lower = prompt.lower()

        if "remember" in prompt_lower and "preference" in prompt_lower:
            # Save preference
            return BridgeResponse(
                success=True,
                data={"note": "Use add_to_memory() directly"},
                timing_ms=(time.time() - start_time) * 1000,
                source="memory_bridge",
            )
        else:
            # Search memory
            results = memory.search(prompt, limit=5)
            return BridgeResponse(
                success=True,
                data={"memories": results},
                timing_ms=(time.time() - start_time) * 1000,
                source="memory_bridge",
            )

    async def _handle_coding(self, prompt: str, start_time: float) -> BridgeResponse:
        """Handle coding tasks - route to tool bridge"""
        tools = self.bridges.get("tools")

        if not tools:
            return BridgeResponse(success=False, error="Tool bridge not available")

        # Check for code execution request
        if "run" in prompt.lower() and (
            "code" in prompt.lower() or "script" in prompt.lower()
        ):
            return BridgeResponse(
                success=True,
                data={
                    "note": "Use tool bridge execute() with run_command or execute_code"
                },
                timing_ms=(time.time() - start_time) * 1000,
                source="tool_bridge",
            )

        return BridgeResponse(success=False, data=None, source="orchestrator")

    async def _handle_council(self, prompt: str, start_time: float) -> BridgeResponse:
        """Handle quantum council"""
        council = self.bridges.get("council")

        if not council:
            return BridgeResponse(success=False, error="Quantum Council not available")

        try:
            result = await council.query(prompt)
            return BridgeResponse(
                success=True,
                data=result,
                timing_ms=(time.time() - start_time) * 1000,
                source="quantum_council",
            )
        except Exception as e:
            return BridgeResponse(success=False, error=str(e))

    def get_status(self) -> Dict:
        """Get comprehensive status"""
        return {
            "bridges": {
                name: {"available": True, "type": type(bridge).__name__}
                for name, bridge in self.bridges.items()
            },
            "network": self.bridges.get("network", {}).get_network_status()
            if hasattr(self.bridges.get("network"), "get_network_status")
            else {},
        }

    def get_capabilities(self) -> List[str]:
        """Get all available capabilities"""
        caps = []

        if "memory" in self.bridges:
            caps.extend(["memory_search", "memory_save", "preferences"])

        if "tools" in self.bridges:
            caps.extend(
                ["web_search", "run_command", "read_file", "write_file", "execute_code"]
            )

        if "computer" in self.bridges:
            caps.extend(["screenshot", "click", "type", "hotkey", "scroll"])

        if "browser" in self.bridges:
            caps.extend(["web_search", "page_fetch", "form_fill"])

        if "calendar" in self.bridges:
            caps.extend(["get_events", "create_event"])

        if "council" in self.bridges:
            caps.extend(["parallel_query", "multi_model_synthesis"])

        return caps


# Global orchestrator
_orchestrator: Optional[UnifiedBridgeOrchestrator] = None


def get_orchestrator() -> UnifiedBridgeOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = UnifiedBridgeOrchestrator()
    return _orchestrator


# Quick functions
async def orchestrate(prompt: str, context: Dict = None) -> BridgeResponse:
    """Quick orchestrate function"""
    return await get_orchestrator().execute(prompt, context)


def get_all_capabilities() -> List[str]:
    """Get all system capabilities"""
    return get_orchestrator().get_capabilities()


if __name__ == "__main__":

    async def test():
        orch = get_orchestrator()

        print("\n=== Capabilities ===")
        print(orch.get_capabilities())

        print("\n=== Status ===")
        print(json.dumps(orch.get_status(), indent=2))

        print("\n=== Test Tasks ===")

        # Test calendar
        result = await orch.execute("What's on my calendar this week?")
        print(f"\nCalendar: {result.success}")

        # Test search
        result = await orch.execute("search for AI news")
        print(f"Search: {result.success}")

        # Test memory
        result = await orch.execute("what do you remember about me")
        print(f"Memory: {result.success}")

    asyncio.run(test())
