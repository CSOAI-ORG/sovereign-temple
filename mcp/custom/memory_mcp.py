#!/usr/bin/env python3
"""
Memory MCP Server - Exposes SOV3 Memory Hub via MCP Protocol
"""

import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sov3_memory_hub import get_memory_hub


class MemoryMCPServer:
    """MCP Server for Memory operations"""

    def __init__(self):
        self.memory = get_memory_hub()

    def handle_request(self, method, params):
        """Handle MCP request"""

        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "memory_add",
                        "description": "Add a memory",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "memory_type": {
                                    "type": "string",
                                    "enum": ["episodic", "semantic", "working"],
                                },
                                "importance": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                },
                            },
                            "required": ["content"],
                        },
                    },
                    {
                        "name": "memory_search",
                        "description": "Search memories",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "limit": {"type": "integer", "default": 5},
                            },
                        },
                    },
                    {
                        "name": "memory_stats",
                        "description": "Get memory statistics",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "memory_add":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                self.memory.add(
                                    content=args.get("content", ""),
                                    memory_type=args.get("memory_type", "episodic"),
                                    importance=args.get("importance", 0.5),
                                )
                            ),
                        }
                    ]
                }

            elif tool_name == "memory_search":
                results = self.memory.search(
                    query=args.get("query", ""), limit=args.get("limit", 5)
                )
                return {
                    "content": [{"type": "text", "text": json.dumps(results, indent=2)}]
                }

            elif tool_name == "memory_stats":
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(self.memory.stats(), indent=2),
                        }
                    ]
                }

        return {"error": f"Unknown method: {method}"}


def main():
    """Run MCP server"""
    server = MemoryMCPServer()

    # Simple stdio communication
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = server.handle_request(
                request.get("method", ""), request.get("params", {})
            )

            print(json.dumps(response))
            sys.stdout.flush()

        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
