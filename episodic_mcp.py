#!/usr/bin/env python3
"""
SOV3 Episodic Memory MCP Server
===============================
Provides MCP tool for searching SOV3 episodic memories.
Run standalone: python3 episodic_mcp.py
Or integrated into existing MCP server.
"""

import json
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

EPISODIC_DIR = Path.home() / "clawd" / "sovereign-temple" / "memory" / "episodic"
CACHE_FILE = Path.home() / "clawd" / "sovereign-temple" / "memory_cache.json"


def build_cache():
    """Build/search memory index."""
    if CACHE_FILE.exists():
        age = datetime.now() - datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        if age.seconds < 300:
            with open(CACHE_FILE) as f:
                return json.load(f)

    index = []
    if EPISODIC_DIR.exists():
        for f in EPISODIC_DIR.glob("*.json"):
            try:
                with open(f) as file:
                    data = json.load(file)
                    index.append(
                        {
                            "id": data.get("id", f.stem),
                            "content": data.get("content", ""),
                            "type": data.get("type", "unknown"),
                            "importance": data.get("importance", 0.5),
                            "timestamp": data.get("timestamp", ""),
                            "tags": data.get("tags", []),
                        }
                    )
            except:
                pass

    with open(CACHE_FILE, "w") as f:
        json.dump(index, f)
    return index


def search(query: str, limit: int = 10, memory_type: str = None):
    """Search memories."""
    index = build_cache()
    query_lower = query.lower()
    results = []

    for mem in index:
        content = mem.get("content", "").lower()
        tags = [t.lower() for t in mem.get("tags", [])]

        score = 0
        if query_lower in content:
            score = 1.0
        elif any(query_lower in tag for tag in tags):
            score = 0.8
        elif any(word in content for word in query_lower.split()):
            score = 0.5

        if score > 0 and (memory_type is None or mem.get("type") == memory_type):
            mem["score"] = score
            results.append(mem)

    results.sort(key=lambda x: (-x.get("score", 0), -x.get("importance", 0)))
    return results[:limit]


class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/mcp":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(content_length))

        method = payload.get("method", "")
        request_id = payload.get("id", 1)

        result = {"jsonrpc": "2.0", "id": request_id}

        if method == "tools/list":
            result["result"] = {
                "tools": [
                    {
                        "name": "search_episodic",
                        "description": "Search SOV3 episodic memories for relevant context",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "limit": {"type": "integer", "default": 10},
                                "memory_type": {"type": "string"},
                            },
                        },
                    },
                    {
                        "name": "get_memory_stats",
                        "description": "Get memory system statistics",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            }

        elif method == "tools/call":
            params = payload.get("params", {})
            tool_name = params.get("name", "")
            args = params.get("arguments", {})

            if tool_name == "search_episodic":
                results = search(
                    query=args.get("query", ""),
                    limit=args.get("limit", 10),
                    memory_type=args.get("memory_type"),
                )
                result["result"] = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {"results": results, "count": len(results)}
                            ),
                        }
                    ]
                }

            elif tool_name == "get_memory_stats":
                index = build_cache()
                by_type = {}
                for mem in index:
                    t = mem.get("type", "unknown")
                    by_type[t] = by_type.get(t, 0) + 1

                result["result"] = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "total_memories": len(index),
                                    "by_type": by_type,
                                    "cache_age_seconds": (
                                        datetime.now()
                                        - datetime.fromtimestamp(
                                            CACHE_FILE.stat().st_mtime
                                        )
                                    ).seconds
                                    if CACHE_FILE.exists()
                                    else 0,
                                }
                            ),
                        }
                    ]
                }
            else:
                result["error"] = f"Unknown tool: {tool_name}"

        else:
            result["error"] = f"Unknown method: {method}"

        self.send_response(200 if "error" not in result else 400)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def log_message(self, format, *args):
        pass


def main():
    port = 3103
    server = HTTPServer(("0.0.0.0", port), MCPHandler)
    print(f"🔍 SOV3 Episodic MCP Server running on port {port}")
    print(f"   Endpoint: http://localhost:{port}/mcp")
    print(f"   Tools: search_episodic, get_memory_stats")
    server.serve_forever()


if __name__ == "__main__":
    main()
