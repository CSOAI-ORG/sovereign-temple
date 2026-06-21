#!/usr/bin/env python3
"""
SOV3 Episodic Memory MCP Wrapper
================================
Adds search_episodic MCP tool that queries ~/clawd/sovereign-temple/memory/episodic/
Run: python3 search_episodic_mcp.py
"""

import sys
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EPISODIC_DIR = Path.home() / "clawd" / "sovereign-temple" / "memory" / "episodic"
CACHE_FILE = Path.home() / "clawd" / "sovereign-temple" / "memory_index.json"


def build_memory_index():
    """Build an in-memory index of all episodic memories for fast search."""
    if CACHE_FILE.exists():
        age = datetime.now() - datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        if age.seconds < 300:  # 5 min cache
            with open(CACHE_FILE) as f:
                return json.load(f)

    index = []
    if EPISODIC_DIR.exists():
        for f in EPISODIC_DIR.glob("*.json"):
            try:
                with open(f) as file:
                    data = json.load(file)
                    content = data.get("content", "")
                    index.append(
                        {
                            "id": data.get("id", f.stem),
                            "content": content,
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


def search_episodic(query: str, limit: int = 10, memory_type: str = None):
    """Search episodic memories by content or tags."""
    index = build_memory_index()
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


def format_results(results):
    """Format search results for MCP response."""
    return {
        "results": [
            {
                "id": r["id"],
                "content": r["content"],
                "type": r["type"],
                "importance": r["importance"],
                "timestamp": r["timestamp"],
                "tags": r.get("tags", []),
            }
            for r in results
        ],
        "count": len(results),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Search SOV3 episodic memories")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Max results")
    parser.add_argument("--type", help="Filter by memory type")

    args = parser.parse_args()

    results = search_episodic(args.query, args.limit, args.type)
    print(json.dumps(format_results(results), indent=2))
