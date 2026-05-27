#!/usr/bin/env python3
"""
SOV3 Tool Bridge - Unified Tool Execution Layer
Connects to MCP servers, handles function calling, and manages tool execution
"""

import json
import os
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import requests


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict
    handler: Optional[Callable] = None


class SOV3ToolBridge:
    """
    Unified tool execution layer
    - MCP server connections
    - Function calling with structured output
    - Tool result formatting for LLM
    """

    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.mcp_servers: List[Dict] = []
        self._setup_core_tools()

    def _setup_core_tools(self):
        """Define core SOV3 tools"""

        # Memory tools
        self.register_tool(
            ToolDefinition(
                name="memory_search",
                description="Search past conversations and memories",
                parameters={
                    "query": {"type": "string", "description": "What to search for"},
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 5,
                    },
                },
            )
        )

        self.register_tool(
            ToolDefinition(
                name="memory_save",
                description="Save important information to memory",
                parameters={
                    "content": {"type": "string", "description": "What to remember"},
                    "importance": {
                        "type": "number",
                        "description": "0-1 importance",
                        "default": 0.5,
                    },
                },
            )
        )

        # Web tools
        self.register_tool(
            ToolDefinition(
                name="web_search",
                description="Search the web for information",
                parameters={
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 5,
                    },
                },
            )
        )

        self.register_tool(
            ToolDefinition(
                name="web_fetch",
                description="Fetch content from a URL",
                parameters={
                    "url": {"type": "string", "description": "URL to fetch"},
                    "max_chars": {
                        "type": "integer",
                        "description": "Max characters",
                        "default": 2000,
                    },
                },
            )
        )

        # System tools
        self.register_tool(
            ToolDefinition(
                name="run_command",
                description="Execute a shell command",
                parameters={
                    "command": {"type": "string", "description": "Command to run"},
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout seconds",
                        "default": 30,
                    },
                },
            )
        )

        self.register_tool(
            ToolDefinition(
                name="read_file",
                description="Read a file from the filesystem",
                parameters={
                    "path": {"type": "string", "description": "File path"},
                    "max_lines": {
                        "type": "integer",
                        "description": "Max lines",
                        "default": 100,
                    },
                },
            )
        )

        self.register_tool(
            ToolDefinition(
                name="write_file",
                description="Write content to a file",
                parameters={
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write"},
                },
            )
        )

        # Agent tools
        self.register_tool(
            ToolDefinition(
                name="delegate_agent",
                description="Delegate a task to an OpenClaw agent",
                parameters={
                    "agent": {"type": "string", "description": "Agent name"},
                    "task": {"type": "string", "description": "Task description"},
                },
            )
        )

        # Code execution
        self.register_tool(
            ToolDefinition(
                name="execute_code",
                description="Execute Python code in a sandbox",
                parameters={
                    "code": {"type": "string", "description": "Python code to run"},
                    "language": {
                        "type": "string",
                        "description": "Language",
                        "default": "python",
                    },
                },
            )
        )

        # Calendar/Time
        self.register_tool(
            ToolDefinition(
                name="get_time",
                description="Get current time and date",
                parameters={
                    "timezone": {
                        "type": "string",
                        "description": "Timezone",
                        "default": "local",
                    }
                },
            )
        )

        self.register_tool(
            ToolDefinition(
                name="calendar_events",
                description="Get upcoming calendar events",
                parameters={
                    "days": {
                        "type": "integer",
                        "description": "Days ahead",
                        "default": 7,
                    }
                },
            )
        )

        print(f"🔧 SOV3 Tool Bridge: {len(self.tools)} core tools registered")

    def register_tool(self, tool: ToolDefinition):
        """Register a tool"""
        self.tools[tool.name] = tool

    def get_tool_schemas(self) -> List[Dict]:
        """Get tool schemas for LLM function calling"""
        schemas = []
        for name, tool in self.tools.items():
            schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
            }

            for param_name, param_info in tool.parameters.items():
                schema["function"]["parameters"]["properties"][param_name] = {
                    "type": param_info.get("type", "string"),
                    "description": param_info.get("description", ""),
                }
                if "default" not in param_info:
                    schema["function"]["parameters"]["required"].append(param_name)

            schemas.append(schema)

        return schemas

    async def execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Execute a tool by name with arguments"""
        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        tool = self.tools[tool_name]

        # Execute based on tool name
        try:
            if tool_name == "memory_search":
                from sov3_memory_hub import recall

                results = recall(arguments.get("query", ""), arguments.get("limit", 5))
                return {"results": [r.get("content", "") for r in results]}

            elif tool_name == "memory_save":
                from sov3_memory_hub import add_to_memory

                add_to_memory(
                    arguments.get("content", ""),
                    importance=arguments.get("importance", 0.5),
                )
                return {"success": True, "message": "Memory saved"}

            elif tool_name == "web_search":
                return await self._web_search(
                    arguments.get("query", ""), arguments.get("num_results", 5)
                )

            elif tool_name == "run_command":
                import subprocess

                result = subprocess.run(
                    arguments.get("command", ""),
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=arguments.get("timeout", 30),
                )
                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

            elif tool_name == "read_file":
                path = arguments.get("path", "")
                max_lines = arguments.get("max_lines", 100)
                try:
                    with open(path, "r") as f:
                        lines = [f.readline() for _ in range(max_lines)]
                        content = "".join(lines)
                    return {"content": content}
                except Exception as e:
                    return {"error": str(e)}

            elif tool_name == "write_file":
                path = arguments.get("path", "")
                content = arguments.get("content", "")
                try:
                    with open(path, "w") as f:
                        f.write(content)
                    return {"success": True}
                except Exception as e:
                    return {"error": str(e)}

            elif tool_name == "get_time":
                from datetime import datetime

                return {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp": datetime.now().isoformat(),
                }

            elif tool_name == "calendar_events":
                # Placeholder - integrate with calendar API
                return {"events": [], "message": "Calendar integration not configured"}

            elif tool_name == "delegate_agent":
                # Placeholder for OpenClaw integration
                return {"message": f"Delegated to {arguments.get('agent', 'unknown')}"}

            else:
                return {"error": f"Tool not implemented: {tool_name}"}

        except Exception as e:
            return {"error": str(e)}

    async def _web_search(self, query: str, num_results: int) -> Dict:
        """Simple web search using DuckDuckGo"""
        try:
            from duckduckgo_search import DDGS

            ddgs = DDGS()
            results = list(ddgs.text(query, max_results=num_results))
            return {"results": [r.get("body", "") for r in results]}
        except Exception as e:
            # Fallback to simple search
            return {"results": [], "error": str(e)}


# Global tool bridge
_tool_bridge: Optional[SOV3ToolBridge] = None


def get_tool_bridge() -> SOV3ToolBridge:
    global _tool_bridge
    if _tool_bridge is None:
        _tool_bridge = SOV3ToolBridge()
    return _tool_bridge


# Quick functions
def get_schemas():
    """Get tool schemas for LLM"""
    return get_tool_bridge().get_tool_schemas()


async def execute(tool_name: str, args: Dict) -> Dict:
    """Execute a tool"""
    return await get_tool_bridge().execute_tool(tool_name, args)


if __name__ == "__main__":
    bridge = get_tool_bridge()
    print("=== SOV3 Tool Bridge ===")
    print(f"Tools: {list(bridge.tools.keys())}")
    print(f"\nSchemas: {json.dumps(bridge.get_tool_schemas()[:2], indent=2)}")
