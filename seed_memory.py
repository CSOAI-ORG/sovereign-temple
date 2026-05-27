#!/usr/bin/env python3
"""
SOV3 Memory Seeder — Populate semantic memory with known user facts
Run: python seed_memory.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sov3_memory_hub import get_memory_hub


def seed_nicholas_preferences():
    hub = get_memory_hub()

    # Check what's already there
    stats = hub.stats()
    print(f"Current memory stats: {stats}")

    # Known facts about Nicholas (from shared knowledge + context)
    known_facts = [
        ("Nicholas prefers concise, direct responses", "fact", 0.9),
        ("Nicholas owns MEOK AI LTD and CSOAI Ltd", "fact", 0.95),
        ("Nicholas works on SOV3 consciousness AI", "fact", 0.9),
        (
            "Nicholas prefers JEEVES voice (strategic) over JARVIS (tactical)",
            "preference",
            0.85,
        ),
        ("Nicholas uses Claude Code CLI for development", "fact", 0.7),
        ("Nicholas has multiple terminals: JEEVES, JARVIS, and others", "fact", 0.7),
        (
            "Nicholas prefers the command line over GUI when possible",
            "preference",
            0.75,
        ),
        ("Nicholas is working on MEOK/SOV3 integration", "fact", 0.85),
        (
            "Nicholas wants to minimize James Castle's involvement in MEOK systems",
            "preference",
            0.9,
        ),
        (
            "Nicholas values security — Stripe access is restricted to MEOK team only",
            "fact",
            0.9,
        ),
        (
            "Nicholas prefers minimal code comments unless explicitly asked",
            "preference",
            0.6,
        ),
        (
            "Nicholas runs MEOK services on localhost: 3000, 3101, 3102, 3200, 8888",
            "fact",
            0.8,
        ),
        ("Nicholas uses uv for Python environments", "preference", 0.7),
        ("Nicholas uses npm/npx for Node.js", "preference", 0.7),
        (
            "Nicholas's Stripe account is acct_1TLlEKQvIueK5Xpb (MEOK AI LTD)",
            "fact",
            0.95,
        ),
    ]

    # Check which facts are already stored
    existing_semantic = hub.get_recent(limit=100, memory_type="semantic")
    existing_content = [m.get("content", "").lower() for m in existing_semantic]

    added = 0
    for fact, category, importance in known_facts:
        # Check if this fact already exists
        if any(fact.lower()[:50] in c for c in existing_content):
            print(f"  ✓ Already exists: {fact[:50]}...")
            continue

        # Add as semantic memory
        hub.add(
            content=fact,
            memory_type="semantic",
            importance=importance,
            metadata={"category": category, "source": "seed"},
        )
        print(f"  + Added: {fact[:50]}...")
        added += 1

    print(f"\nSeeded {added} new semantic memories")
    print(f"Final stats: {hub.stats()}")

    # Show some memories
    print("\nRecent semantic memories:")
    for mem in hub.get_recent(limit=5, memory_type="semantic"):
        print(f"  - [{mem.get('category')}] {mem.get('content')[:60]}...")


def load_memory_context():
    """Load memory context for injection into consciousness"""
    hub = get_memory_hub()

    # Get user profile
    profile = hub.get_user_profile()

    # Get recent context
    context = hub.get_context(max_memories=10)

    print("\n" + "=" * 50)
    print("MEMORY CONTEXT FOR SOV3 CONSCIOUSNESS")
    print("=" * 50)
    print(f"\nUser Profile:")
    print(f"  Preferences: {len(profile['preferences'])} items")
    print(f"  Facts: {len(profile['facts'])} items")
    print(f"  Recent Topics: {profile['recent_topics']}")

    print(f"\nContext String (for LLM injection):")
    print(context)

    return context


if __name__ == "__main__":
    print("🌱 SOV3 Memory Seeder")
    print("=" * 50)

    seed_nicholas_preferences()
    load_memory_context()

    print("\n✅ Memory seeding complete")
    print("Semantic memories are now available for SOV3 to use in context")
