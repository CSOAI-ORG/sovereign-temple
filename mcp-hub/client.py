"""MCP Client Hub — Connects MEOKCLAW to the MCP ecosystem."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, AsyncIterator


@dataclass
class MCPServerConfig:
    name: str
    transport: str  # "stdio", "sse", "http"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30


class MCPClientHub:
    """Manages connections to multiple MCP servers."""

    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._tools_cache: Dict[str, List[Dict]] = {}
        self._connected: set = set()

    def register_server(self, config: MCPServerConfig):
        """Register an MCP server configuration."""
        self._servers[config.name] = config

    async def discover_tools(self, server_name: Optional[str] = None) -> List[Dict]:
        """Discover available tools from all or specific server."""
        tools = []
        servers = [server_name] if server_name else list(self._servers.keys())
        for name in servers:
            if name in self._tools_cache:
                tools.extend(self._tools_cache[name])
            else:
                # In real implementation: call MCP server via JSON-RPC
                # tools/list method
                discovered = await self._fetch_tools(name)
                self._tools_cache[name] = discovered
                tools.extend(discovered)
        return tools

    async def _fetch_tools(self, server_name: str) -> List[Dict]:
        """Fetch tools from a specific MCP server."""
        # Placeholder: real implementation uses mcp SDK
        # from mcp import ClientSession, StdioServerParameters
        return []

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Call a tool on a specific MCP server."""
        # Placeholder: real implementation uses mcp SDK
        return {"result": f"Called {tool_name} on {server_name}", "arguments": arguments}

    def get_tool_schema(self, tool_name: str) -> Optional[Dict]:
        """Get JSON schema for a specific tool."""
        for server_tools in self._tools_cache.values():
            for tool in server_tools:
                if tool.get("name") == tool_name:
                    return tool.get("inputSchema")
        return None

    async def call_with_auto_discovery(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Auto-discover which server has the tool and call it."""
        for server_name, tools in self._tools_cache.items():
            if any(t.get("name") == tool_name for t in tools):
                return await self.call_tool(server_name, tool_name, arguments)
        # Discover first
        await self.discover_tools()
        for server_name, tools in self._tools_cache.items():
            if any(t.get("name") == tool_name for t in tools):
                return await self.call_tool(server_name, tool_name, arguments)
        return {"error": f"Tool {tool_name} not found in any MCP server"}

    def list_builtin_servers(self) -> List[MCPServerConfig]:
        """Return list of commonly useful MCP servers."""
        return [
            MCPServerConfig("github", "stdio", "npx", ["-y", "@modelcontextprotocol/server-github"]),
            MCPServerConfig("playwright", "stdio", "npx", ["-y", "@anthropic-ai/mcp-playwright"]),
            MCPServerConfig("brave-search", "stdio", "npx", ["-y", "@modelcontextprotocol/server-brave-search"]),
            MCPServerConfig("filesystem", "stdio", "npx", ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]),
            MCPServerConfig("postgres", "stdio", "npx", ["-y", "@modelcontextprotocol/server-postgres"]),
        ]
