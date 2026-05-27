#!/usr/bin/env python3
"""
SOV3 Memory Persistence Layer

Lightweight SQLite backup/restore for SOV3 memory episodes.
Survives restarts without requiring PostgreSQL or Weaviate.

Usage:
    from sov3_persistence import persist_memory, load_memory
    persist_memory(episodes, "data/sov3_memory.sqlite")
    episodes = load_memory("data/sov3_memory.sqlite")
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional


def _ensure_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_episodes (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            importance_score REAL DEFAULT 0.0,
            care_weight REAL DEFAULT 0.0,
            source_agent TEXT DEFAULT '',
            memory_type TEXT DEFAULT 'interaction',
            related_episodes TEXT DEFAULT '[]',
            tags TEXT DEFAULT '[]',
            access_count INTEGER DEFAULT 0,
            last_accessed TEXT,
            compacted_from TEXT DEFAULT '[]'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()


def persist_memory(episodes: List[Dict[str, Any]], db_path: str = "data/sov3_memory.sqlite"):
    """Persist memory episodes to SQLite."""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    _ensure_table(conn)
    
    for ep in episodes:
        conn.execute("""
            INSERT OR REPLACE INTO memory_episodes VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            ep.get("id", ""),
            ep.get("content", ""),
            ep.get("timestamp", datetime.utcnow().isoformat()),
            ep.get("importance_score", 0.0),
            ep.get("care_weight", 0.0),
            ep.get("source_agent", ""),
            ep.get("memory_type", "interaction"),
            json.dumps(ep.get("related_episodes", [])),
            json.dumps(ep.get("tags", [])),
            ep.get("access_count", 0),
            ep.get("last_accessed"),
            json.dumps(ep.get("compacted_from", [])),
        ))
    
    conn.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (
        "last_persisted",
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()


def load_memory(db_path: str = "data/sov3_memory.sqlite") -> List[Dict[str, Any]]:
    """Load memory episodes from SQLite."""
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT * FROM memory_episodes ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    
    episodes = []
    for row in rows:
        episodes.append({
            "id": row[0],
            "content": row[1],
            "timestamp": row[2],
            "importance_score": row[3],
            "care_weight": row[4],
            "source_agent": row[5],
            "memory_type": row[6],
            "related_episodes": json.loads(row[7]),
            "tags": json.loads(row[8]),
            "access_count": row[9],
            "last_accessed": row[10],
            "compacted_from": json.loads(row[11]),
        })
    return episodes


def get_persisted_count(db_path: str = "data/sov3_memory.sqlite") -> int:
    """Get count of persisted episodes."""
    if not os.path.exists(db_path):
        return 0
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM memory_episodes")
    count = cursor.fetchone()[0]
    conn.close()
    return count


if __name__ == "__main__":
    import sys
    db = sys.argv[1] if len(sys.argv) > 1 else "data/sov3_memory.sqlite"
    eps = load_memory(db)
    print(f"SOV3 Persistence: {len(eps)} episodes in {db}")
    if eps:
        print(f"  Latest: {eps[0]['timestamp']} — {eps[0]['content'][:60]}...")
