#!/usr/bin/env python3
"""
Memory Bridge - Persistent Memory for SOV3
Integrates with Mem0/Zep-style memory architecture
Stores: episodic, semantic, working memory
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import hashlib


class SOV3MemoryBridge:
    """
    Persistent memory layer for SOV3 consciousness
    Tiered storage: working, session, long-term
    """

    def __init__(self, base_dir: str = "/Users/nicholas/clawd/sovereign-temple/memory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

        # Memory tiers
        self.working_dir = self.base_dir / "working"
        self.session_dir = self.base_dir / "session"
        self.longterm_dir = self.base_dir / "longterm"
        self.episodic_dir = self.base_dir / "episodic"

        for d in [
            self.working_dir,
            self.session_dir,
            self.longterm_dir,
            self.episodic_dir,
        ]:
            d.mkdir(exist_ok=True)

        # Current session
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    def store_episode(
        self, episode_type: str, content: str, metadata: Dict = None
    ) -> str:
        """Store an episodic memory (conversation, action, event)"""
        episode_id = hashlib.md5(f"{time.time()}_{content[:50]}".encode()).hexdigest()[
            :12
        ]

        episode = {
            "id": episode_id,
            "type": episode_type,  # conversation, action, event, reflection
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "metadata": metadata or {},
            "importance": self._compute_importance(content),
        }

        path = self.episodic_dir / f"{episode_id}.json"
        path.write_text(json.dumps(episode, indent=2))

        # Also store in session for quick access
        session_path = self.session_dir / f"{episode_id}.json"
        session_path.write_text(json.dumps(episode, indent=2))

        return episode_id

    def _compute_importance(self, content: str) -> float:
        """Compute importance score based on keywords and length"""
        importance_keywords = [
            "important",
            "remember",
            "decision",
            "plan",
            "goal",
            "commitment",
            "promise",
            "agreement",
            "learning",
            "insight",
            " breakthrough",
            "achievement",
            "error",
            "fix",
        ]
        score = 0.5
        content_lower = content.lower()

        for kw in importance_keywords:
            if kw in content_lower:
                score += 0.1

        # Cap at 1.0
        return min(score, 1.0)

    def recall(
        self, query: str, limit: int = 10, session_only: bool = False
    ) -> List[Dict]:
        """Recall memories matching query (simple keyword search)"""
        search_dir = self.session_dir if session_only else self.episodic_dir
        results = []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        for path in sorted(search_dir.glob("*.json"), key=lambda p: -p.stat().st_mtime):
            try:
                episode = json.loads(path.read_text())
                content_lower = episode.get("content", "").lower()

                # Simple relevance scoring
                matches = sum(1 for w in query_words if w in content_lower)
                if matches > 0:
                    episode["relevance"] = matches
                    results.append(episode)

                if len(results) >= limit:
                    break
            except:
                continue

        # Sort by relevance then importance
        results.sort(
            key=lambda x: (x.get("relevance", 0), x.get("importance", 0)), reverse=True
        )
        return results[:limit]

    def store_knowledge(self, key: str, value: Any, category: str = "general") -> None:
        """Store semantic knowledge (facts, preferences, learnings)"""
        knowledge = {
            "key": key,
            "value": value,
            "category": category,  # preference, fact, skill, learning
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        path = self.longterm_dir / f"{hashlib.md5(key.encode()).hexdigest()[:16]}.json"
        path.write_text(json.dumps(knowledge, indent=2))

    def get_knowledge(self, key: str) -> Optional[Any]:
        """Retrieve semantic knowledge"""
        path = self.longterm_dir / f"{hashlib.md5(key.encode()).hexdigest()[:16]}.json"
        if path.exists():
            return json.loads(path.read_text()).get("value")
        return None

    def update_working_memory(self, key: str, value: Any) -> None:
        """Update working memory (current context)"""
        working = {
            "key": key,
            "value": value,
            "updated_at": datetime.now().isoformat(),
        }

        path = self.working_dir / f"{key}.json"
        path.write_text(json.dumps(working, indent=2))

    def get_working_memory(self, key: str) -> Optional[Any]:
        """Get working memory value"""
        path = self.working_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text()).get("value")
        return None

    def get_working_context(self) -> Dict:
        """Get all working memory as context"""
        context = {}
        for path in self.working_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                context[data.get("key", path.stem)] = data.get("value")
            except:
                continue
        return context

    def consolidate_session(self) -> int:
        """Move session memories to long-term storage"""
        count = 0
        for path in self.session_dir.glob("*.json"):
            try:
                episode = json.loads(path.read_text())
                if episode.get("importance", 0) > 0.7:
                    # Keep important in episodic
                    count += 1
                else:
                    # Delete less important
                    path.unlink()
            except:
                continue
        return count

    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        return {
            "episodic_count": len(list(self.episodic_dir.glob("*.json"))),
            "session_count": len(list(self.session_dir.glob("*.json"))),
            "knowledge_count": len(list(self.longterm_dir.glob("*.json"))),
            "working_count": len(list(self.working_dir.glob("*.json"))),
            "current_session": self.session_id,
        }


# Global instance
_memory_bridge: Optional[SOV3MemoryBridge] = None


def get_memory_bridge() -> SOV3MemoryBridge:
    global _memory_bridge
    if _memory_bridge is None:
        _memory_bridge = SOV3MemoryBridge()
    return _memory_bridge


if __name__ == "__main__":
    # Test
    mb = get_memory_bridge()

    # Store a conversation
    mb.store_episode(
        "conversation", "User asked about gemma 4 integration", {"user": "nick"}
    )

    # Store knowledge
    mb.store_knowledge("preferred_voice", "bm_daniel", "preference")

    # Update working memory
    mb.update_working_memory("current_task", "Voice pipeline integration")

    # Recall
    results = mb.recall("gemma")
    print(f"Found {len(results)} memories")

    # Stats
    print(mb.get_memory_stats())
