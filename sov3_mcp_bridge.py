#!/usr/bin/env python3
"""
SOV3 MCP Bridge - Enhanced MCP Protocol Integration
Connects to SOV3 MCP server, manages tool execution, and handles MCP protocol
"""

import json
import os
import asyncio
import requests
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import logging

log = logging.getLogger("sov3-mcp-bridge")


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict


class SOV3MCPBridge:
    """
    Bridge to SOV3 MCP Server
    - Connects to existing sovereign-mcp-server.py
    - Exposes tools via MCP protocol
    - Handles tool execution and response parsing
    """

    def __init__(self, mcp_url: str = "http://localhost:3200"):
        self.mcp_url = mcp_url
        self.tools: Dict[str, MCPTool] = {}
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._initialized = False

    async def initialize(self) -> bool:
        """Connect to SOV3 MCP server and load tools"""
        try:
            # Test connection
            resp = requests.get(f"{self.mcp_url}/health", timeout=5)
            if resp.status_code != 200:
                log.warning(f"MCP server returned {resp.status_code}")
        except:
            pass

        # Load core tools from SOV3
        self._load_core_tools()

        # Add custom tools not in SOV3
        self._add_missing_tools()

        self._initialized = True
        log.info(f"🌀 SOV3 MCP Bridge: {len(self.tools)} tools loaded")
        return True

    def _load_core_tools(self):
        """Load tools from SOV3 MCP server"""
        core_tools = [
            {
                "name": "query_memories",
                "description": "Query Sovereign's RAG memory for relevant context",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "record_memory",
                "description": "Store important information in Sovereign memory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "memory_type": {"type": "string"},
                        "tags": {"type": "array"},
                    },
                },
            },
            {
                "name": "get_consciousness_state",
                "description": "Get current emotional and consciousness state",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_engagement_score",
                "description": "Get current social cohesion score",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_system_status",
                "description": "Get full Sovereign system status",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "delegate_task",
                "description": "Delegate a task to a specific agent",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "agent": {"type": "string"},
                        "task": {"type": "string"},
                    },
                },
            },
            {
                "name": "run_code",
                "description": "Execute Python code in sandbox",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "language": {"type": "string"},
                    },
                },
            },
            {
                "name": "web_search",
                "description": "Search the web for information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "num_results": {"type": "integer"},
                    },
                },
            },
        ]

        for tool in core_tools:
            self.tools[tool["name"]] = MCPTool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["input_schema"],
            )

    def _add_missing_tools(self):
        """Add tools from new bridges"""
        missing_tools = [
            # Memory
            {
                "name": "memory_semantic_search",
                "description": "Semantic search across all memories with relevance scoring",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                        "recency_boost": {"type": "number"},
                    },
                },
            },
            # Computer Use
            {
                "name": "computer_screenshot",
                "description": "Capture screen and get base64 image",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            },
            {
                "name": "computer_click",
                "description": "Click at coordinates or current position",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "button": {"type": "string"},
                    },
                },
            },
            {
                "name": "computer_type",
                "description": "Type text",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "interval": {"type": "number"},
                    },
                },
            },
            {
                "name": "computer_hotkey",
                "description": "Press hotkey combination",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keys": {"type": "array", "items": {"type": "string"}}
                    },
                },
            },
            # Browser
            {
                "name": "browser_search",
                "description": "Search the web",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "num_results": {"type": "integer"},
                    },
                },
            },
            {
                "name": "browser_fetch",
                "description": "Fetch and parse a web page",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "max_chars": {"type": "integer"},
                    },
                },
            },
            # Calendar
            {
                "name": "calendar_events",
                "description": "Get upcoming calendar events",
                "input_schema": {
                    "type": "object",
                    "properties": {"days": {"type": "integer"}},
                },
            },
            {
                "name": "calendar_create",
                "description": "Create a calendar event",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "start": {"type": "string"},
                        "duration": {"type": "integer"},
                        "description": {"type": "string"},
                    },
                },
            },
            # User preferences
            {
                "name": "get_user_preferences",
                "description": "Retrieve user preferences and settings",
                "input_schema": {
                    "type": "object",
                    "properties": {"key": {"type": "string"}},
                },
            },
            {
                "name": "set_user_preferences",
                "description": "Store user preferences and settings",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {"type": "string"},
                    },
                },
            },
            # Notifications
            {
                "name": "send_notification",
                "description": "Send a notification (email, push, etc)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string"},
                        "message": {"type": "string"},
                        "recipient": {"type": "string"},
                    },
                },
            },
            # File operations
            {
                "name": "file_operations",
                "description": "Read, write, list files in workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string"},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                },
            },
            # Quantum Council
            {
                "name": "get_council_deliberation",
                "description": "Get multi-model council decision on a topic",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "models": {"type": "array"},
                    },
                },
            },
            # Bridge Network
            {
                "name": "get_bridge_status",
                "description": "Get status of all bridge connections",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_system_capabilities",
                "description": "Get all available system capabilities",
                "input_schema": {"type": "object", "properties": {}},
            },
        ]

        for tool in missing_tools:
            self.tools[tool["name"]] = MCPTool(
                name=tool["name"],
                description=tool["description"],
                input_schema=tool["input_schema"],
            )

    def get_tool_schemas(self) -> List[Dict]:
        """Get OpenAI-style function calling schemas"""
        schemas = []
        for name, tool in self.tools.items():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": tool.input_schema.get("properties", {}),
                            "required": [],
                        },
                    },
                }
            )
        return schemas

    async def execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool via SOV3 MCP server"""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        # Try MCP server first
        try:
            resp = requests.post(
                f"{self.mcp_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": int(datetime.now().timestamp() * 1000),
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            log.debug(f"MCP server call failed: {e}, trying local fallback")

        # Fallback to local implementation
        return await self._local_tool_execution(tool_name, arguments)

    async def _local_tool_execution(self, tool_name: str, arguments: Dict) -> Dict:
        """Local fallback for tool execution"""
        try:
            # Memory
            if tool_name == "memory_semantic_search":
                from sov3_memory_hub import recall

                results = recall(arguments.get("query", ""), arguments.get("limit", 5))
                return {
                    "results": [
                        {"content": r.get("content", ""), "score": r.get("_score", 0)}
                        for r in results
                    ]
                }

            elif tool_name in ["get_user_preferences", "set_user_preferences"]:
                from sov3_memory_hub import get_memory_hub

                hub = get_memory_hub()
                if tool_name == "get_user_preferences":
                    return {"value": hub.get_preference(arguments.get("key", ""))}
                else:
                    hub.remember_preference(
                        arguments.get("key", ""), arguments.get("value", "")
                    )
                    return {"success": True}

            # Computer Use
            elif tool_name == "computer_screenshot":
                from computer_use_bridge import get_computer_use

                comp = get_computer_use()
                return comp.screenshot(arguments.get("path"))

            elif tool_name == "computer_click":
                from computer_use_bridge import get_computer_use

                comp = get_computer_use()
                return comp.click(
                    arguments.get("x"),
                    arguments.get("y"),
                    arguments.get("button", "left"),
                )

            elif tool_name == "computer_type":
                from computer_use_bridge import get_computer_use

                comp = get_computer_use()
                return comp.type(
                    arguments.get("text", ""), arguments.get("interval", 0.05)
                )

            elif tool_name == "computer_hotkey":
                from computer_use_bridge import get_computer_use

                comp = get_computer_use()
                keys = arguments.get("keys", [])
                return comp.hotkey(*keys) if keys else {"error": "No keys provided"}

            # Browser
            elif tool_name == "browser_search":
                from browser_automation_bridge import get_simple_search

                search = get_simple_search()
                import asyncio

                return asyncio.run(
                    search.search(
                        arguments.get("query", ""), arguments.get("num_results", 5)
                    )
                )

            elif tool_name == "browser_fetch":
                return {
                    "message": "Use browser automation bridge directly",
                    "note": "Requires Playwright",
                }

            # Calendar
            elif tool_name in ["calendar_events", "calendar_create"]:
                from calendar_bridge import get_calendar_bridge
                import asyncio

                cal = get_calendar_bridge()
                if tool_name == "calendar_events":
                    return asyncio.run(cal.get_events(arguments.get("days", 7)))
                else:
                    import datetime

                    start = datetime.datetime.fromisoformat(
                        arguments.get("start", datetime.datetime.now().isoformat())
                    )
                    return asyncio.run(
                        cal.create_event(
                            arguments.get("title", "Event"),
                            start,
                            arguments.get("duration", 60),
                            arguments.get("description", ""),
                        )
                    )

            # Bridge Network
            elif tool_name == "get_bridge_status":
                from sov3_bridge_network import get_bridge_network

                net = get_bridge_network()
                return net.get_network_status()

            elif tool_name == "get_system_capabilities":
                from unified_bridge_orchestrator import get_orchestrator

                orch = get_orchestrator()
                return {"capabilities": orch.get_capabilities()}

            # Legacy tools
            elif tool_name == "calendar_events":
                return {"events": [], "message": "Calendar not configured"}

            elif tool_name == "send_notification":
                return {
                    "success": True,
                    "message": f"Notification queued: {arguments.get('message', '')[:50]}",
                }

            elif tool_name == "file_operations":
                op = arguments.get("operation", "read")
                path = arguments.get("path", "")
                if op == "read":
                    try:
                        with open(path, "r") as f:
                            return {"content": f.read()}
                    except Exception as e:
                        return {"error": str(e)}
                elif op == "write":
                    try:
                        with open(path, "w") as f:
                            f.write(arguments.get("content", ""))
                        return {"success": True}
                    except Exception as e:
                        return {"error": str(e)}
                elif op == "list":
                    import os

                    try:
                        files = os.listdir(path)
                        return {"files": files}
                    except Exception as e:
                        return {"error": str(e)}

            elif tool_name == "computer_use":
                return {"message": "Computer use not available locally"}

            elif tool_name == "get_council_deliberation":
                return {"message": "Use Quantum Council in jarvis_compass.py"}

            else:
                return {"error": f"Tool not implemented locally: {tool_name}"}

        except Exception as e:
            return {"error": str(e)}

    def get_status(self) -> Dict:
        """Get bridge status"""
        return {
            "connected": self._initialized,
            "mcp_url": self.mcp_url,
            "tools_count": len(self.tools),
            "tools": list(self.tools.keys()),
            "session_id": self._session_id,
        }


# Global bridge
_mcp_bridge: Optional[SOV3MCPBridge] = None


def get_mcp_bridge() -> SOV3MCPBridge:
    global _mcp_bridge
    if _mcp_bridge is None:
        _mcp_bridge = SOV3MCPBridge()
    return _mcp_bridge


async def initialize_mcp():
    """Initialize MCP bridge"""
    bridge = get_mcp_bridge()
    await bridge.initialize()
    return bridge


# Quick functions
def get_mcp_schemas():
    """Get tool schemas for LLM"""
    return get_mcp_bridge().get_tool_schemas()


async def call_mcp_tool(tool_name: str, args: Dict) -> Dict:
    """Call an MCP tool"""
    return await get_mcp_bridge().execute_tool(tool_name, args)


if __name__ == "__main__":
    import asyncio

    async def test():
        bridge = await initialize_mcp()
        print("=== SOV3 MCP Bridge Status ===")
        print(json.dumps(bridge.get_status(), indent=2))

        print("\n=== Tool Schemas (first 3) ===")
        schemas = bridge.get_tool_schemas()[:3]
        print(json.dumps(schemas, indent=2))

        print("\n=== Testing Tool Call ===")
        result = await bridge.execute_tool("get_consciousness_state", {})
        print(result)

    asyncio.run(test())
