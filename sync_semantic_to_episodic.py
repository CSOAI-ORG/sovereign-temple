#!/usr/bin/env python3
"""
SOV3 Memory Sync — Sync semantic memories to SOV3 episodic store
This makes semantic memories searchable via MCP tools.
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


def load_sov3_memories():
    """Load the injected memories file."""
    if SOV3_MEMORIES_FILE.exists():
        with open(SOV3_MEMORIES_FILE) as f:
            return json.load(f)
    return {"memories": []}


def save_to_episodic(content: str, memory_type: str, tags: list, importance: float):
    """Save a memory to the episodic store."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    filename = f"sem_{timestamp}_{content_hash}.json"

    filepath = EPISODIC_DIR / filename
    if filepath.exists():
        return False  # Already exists

    memory = {
        "id": filename.replace(".json", ""),
        "content": content,
        "type": memory_type,
        "importance": importance,
        "care_weight": importance,
        "timestamp": datetime.utcnow().isoformat(),
        "session": timestamp,
        "source": "semantic_sync",
        "tags": tags,
    }

    with open(filepath, "w") as f:
        json.dump(memory, f)

    return True


def sync_semantic_to_episodic():
    """Sync semantic memories to episodic store."""
    hub = get_memory_hub()
    sov3_memories = load_sov3_memories()

    print("=== SOV3 Memory Sync ===\n")

    # Get all semantic memories
    semantic_memories = hub.get_recent(limit=200, memory_type="semantic")
    print(f"Semantic memories: {len(semantic_memories)}")

    # Also add key memories from sov3_memories
    key_memories = [
        m
        for m in sov3_memories.get("memories", [])
        if m.get("source") in ["key_facts_injection", "semantic_hub_injection"]
    ]
    print(f"Key memories: {len(key_memories)}")

    synced = 0
    for mem in semantic_memories:
        tags = ["nicholas", "semantic", mem.get("category", "general")]
        if save_to_episodic(
            mem.get("content", ""),
            mem.get("category", "general"),
            tags,
            mem.get("importance", 0.7),
        ):
            synced += 1

    for mem in key_memories:
        tags = mem.get("tags", ["nicholas", "key_memory"])
        if save_to_episodic(
            mem.get("content", ""),
            mem.get("category", "general"),
            tags,
            mem.get("importance", 0.8),
        ):
            synced += 1

    print(f"\n✅ Synced {synced} memories to episodic store")

    # Count episodic files
    episodic_count = len(list(EPISODIC_DIR.glob("*.json")))
    print(f"   Total episodic memories: {episodic_count}")


if __name__ == "__main__":
    sync_semantic_to_episodic()
