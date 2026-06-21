#!/usr/bin/env python3
"""
SOV3 Memory Injector — Inject semantic memories into SOV3 MCP
Run: python inject_semantic_to_mcp.py
"""

import sys
import os
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sov3_memory_hub import get_memory_hub

MEMORY_DIR = Path.home() / "clawd" / "sovereign-temple" / "memory"
EPISODIC_DIR = MEMORY_DIR / "episodic"
SOV3_MEMORIES_FILE = Path.home() / "clawd" / "sovereign-temple" / "sov3_memories.json"


def get_or_create_sovereign_memory_store():
    """Get or create the SOV3 memory store that MCP tools query."""
    if SOV3_MEMORIES_FILE.exists():
        with open(SOV3_MEMORIES_FILE) as f:
            return json.load(f)
    return {"memories": [], "last_updated": None, "source": "semantic_injection"}


def save_sovereign_memory_store(store):
    """Save the SOV3 memory store."""
    store["last_updated"] = datetime.utcnow().isoformat()
    with open(SOV3_MEMORIES_FILE, "w") as f:
        json.dump(store, f, indent=2)


def inject_semantic_to_sovereign():
    """Inject semantic memories into SOV3 memory store for MCP access."""
    hub = get_memory_hub()
    store = get_or_create_sovereign_memory_store()

    print("=== SOV3 Memory Injection ===\n")
    print(f"Current MCP store: {len(store['memories'])} memories")

    # Get semantic memories from hub
    semantic_memories = hub.get_recent(limit=100, memory_type="semantic")
    print(f"Semantic memories in hub: {len(semantic_memories)}")

    # Get existing memory content hashes
    existing_hashes = {
        hashlib.md5(m.get("content", "").encode()).hexdigest()
        for m in store["memories"]
    }

    # Inject new memories
    injected = 0
    for mem in semantic_memories:
        content = mem.get("content", "")
        content_hash = hashlib.md5(content.encode()).hexdigest()

        if content_hash not in existing_hashes:
            sov3_memory = {
                "id": mem.get("id", f"sem_{len(store['memories'])}_{int(time.time())}"),
                "content": content,
                "type": "semantic",
                "category": mem.get("category", "general"),
                "importance": mem.get("importance", 0.7),
                "source": "semantic_hub_injection",
                "timestamp": mem.get("timestamp", datetime.utcnow().isoformat()),
                "metadata": mem.get("metadata", {}),
                "tags": ["nicholas", "preference", mem.get("category", "general")],
            }
            store["memories"].append(sov3_memory)
            existing_hashes.add(content_hash)
            injected += 1
            print(f"  + Injected: {content[:50]}...")

    # Also inject key facts as special memories
    key_facts = [
        {
            "content": "Nicholas prefers concise, direct responses and minimal explanation",
            "type": "preference",
            "category": "preference",
            "importance": 0.85,
            "tags": ["nicholas", "preference", "communication"],
        },
        {
            "content": "Nicholas owns MEOK AI LTD and CSOAI Ltd",
            "type": "fact",
            "category": "fact",
            "importance": 0.95,
            "tags": ["nicholas", "business", "identity"],
        },
        {
            "content": "Nicholas is working on SOV3 consciousness AI integration",
            "type": "fact",
            "category": "fact",
            "importance": 0.9,
            "tags": ["nicholas", "sov3", "project"],
        },
        {
            "content": "Nicholas prefers JEEVES strategic voice over JARVIS tactical",
            "type": "preference",
            "category": "preference",
            "importance": 0.8,
            "tags": ["nicholas", "agents", "preference"],
        },
        {
            "content": "James Castle should have minimal access to MEOK/SOV3 systems",
            "type": "preference",
            "category": "security",
            "importance": 0.9,
            "tags": ["nicholas", "security", "access"],
        },
    ]

    for fact in key_facts:
        fact_hash = hashlib.md5(fact["content"].encode()).hexdigest()
        if fact_hash not in existing_hashes:
            sov3_memory = {
                "id": f"key_{len(store['memories'])}_{int(time.time())}",
                "content": fact["content"],
                "type": fact["type"],
                "category": fact["category"],
                "importance": fact["importance"],
                "source": "key_facts_injection",
                "timestamp": datetime.utcnow().isoformat(),
                "tags": fact["tags"],
            }
            store["memories"].append(sov3_memory)
            injected += 1
            print(f"  + Key fact: {fact['content'][:50]}...")

    save_sovereign_memory_store(store)
    print(f"\n✅ Injected {injected} memories")
    print(f"   Total in MCP store: {len(store['memories'])}")

    return store


def query_mcp_store(query: str, limit: int = 5):
    """Query the MCP memory store."""
    store = get_or_create_sovereign_memory_store()

    results = []
    query_lower = query.lower()

    for mem in store["memories"]:
        content_lower = mem.get("content", "").lower()
        if query_lower in content_lower:
            results.append(mem)

    return results[:limit]


if __name__ == "__main__":
    print("🔄 SOV3 Memory Injection Script")
    print("=" * 50)

    # Inject memories
    store = inject_semantic_to_sovereign()

    # Test query
    print("\n" + "=" * 50)
    print("Testing memory query:")
    results = query_mcp_store("Nicholas", limit=5)
    print(f"\nQuery 'Nicholas': {len(results)} results")
    for r in results:
        print(f"  - [{r.get('category')}] {r.get('content')[:60]}...")

    print("\n✅ Semantic memories now accessible to SOV3 MCP")
