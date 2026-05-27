#!/usr/bin/env python3
"""
SOV3 Memory Hub - Persistent Memory Layer
Implements Mem0-style memory with semantic search, recency weighting, and importance scoring
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import requests


class SOV3MemoryHub:
    """
    Persistent memory system inspired by Mem0
    - Semantic search with vector-like scoring
    - Recency weighting
    - Importance-based retention
    - Cross-session persistence
    """

    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.path.expanduser("~/clawd/sovereign-temple/memory")

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Memory stores
        self.episodic_dir = self.base_dir / "episodic"  # Conversations, events
        self.semantic_dir = self.base_dir / "semantic"  # Facts, preferences
        self.working_dir = self.base_dir / "working"  # Current context

        for d in [self.episodic_dir, self.semantic_dir, self.working_dir]:
            d.mkdir(exist_ok=True)

        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = self.base_dir / "current_session.txt"
        self.session_file.write_text(self.session_id)

        print(f"🧠 SOV3 Memory Hub initialized: {self.session_id}")

    def add(
        self,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5,
        metadata: Dict = None,
    ) -> str:
        """
        Add a memory to the system
        Returns memory ID
        """
        memory_id = hashlib.md5(f"{time.time()}_{content[:50]}".encode()).hexdigest()[
            :16
        ]

        memory = {
            "id": memory_id,
            "content": content,
            "type": memory_type,  # episodic, semantic, working
            "importance": importance,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "metadata": metadata or {},
            # Simple embedding-like features
            "keywords": self._extract_keywords(content),
            "category": self._categorize(content),
        }

        # Store in appropriate directory
        if memory_type == "episodic":
            path = self.episodic_dir / f"{memory_id}.json"
        elif memory_type == "semantic":
            path = self.semantic_dir / f"{memory_id}.json"
        else:
            path = self.working_dir / f"{memory_id}.json"

        path.write_text(json.dumps(memory, indent=2))
        return memory_id

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract simple keywords for matching"""
        # Simple keyword extraction
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "under",
            "again",
            "further",
        }

        words = text.lower().split()
        keywords = [
            w.strip(".,!?;:()[]{}")
            for w in words
            if len(w) > 3 and w.lower() not in stop_words
        ]

        # Return unique keywords
        return list(set(keywords))[:20]

    def _categorize(self, text: str) -> str:
        """Categorize memory"""
        text_lower = text.lower()

        categories = {
            "preference": ["prefer", "like", "want", "wish", "favorite", "hate"],
            "fact": ["is", "are", "was", "wasn't", "isn't", "means", "means"],
            "task": ["todo", "task", "remind", "don't forget", "need to", "should"],
            "conversation": ["said", "asked", "told", "mentioned", "discussed"],
            "knowledge": ["learned", "found", "discovered", "research", "studied"],
            "personal": ["feeling", "emotion", "mood", "excited", "sad", "happy"],
        }

        for cat, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                return cat

        return "general"

    def search(
        self, query: str, limit: int = 5, recency_boost: float = 0.3
    ) -> List[Dict]:
        """
        Search memories - returns most relevant results
        Uses keyword matching + recency + importance scoring
        """
        query_keywords = set(self._extract_keywords(query))
        results = []

        # Search episodic and semantic
        for memory_dir in [self.episodic_dir, self.semantic_dir]:
            for path in memory_dir.glob("*.json"):
                try:
                    memory = json.loads(path.read_text())

                    # Keyword matching score
                    mem_keywords = set(memory.get("keywords", []))
                    keyword_matches = len(query_keywords & mem_keywords)
                    keyword_score = keyword_matches / max(len(query_keywords), 1)

                    # Recency score (more recent = higher)
                    try:
                        mem_time = datetime.fromisoformat(memory["timestamp"])
                        age_hours = (datetime.now() - mem_time).total_seconds() / 3600
                        recency_score = 1.0 / (1.0 + age_hours * recency_boost)
                    except:
                        recency_score = 0.5

                    # Importance score
                    importance_score = memory.get("importance", 0.5)

                    # Total score
                    total_score = (
                        keyword_score * 0.4
                        + recency_score * 0.3
                        + importance_score * 0.3
                    )

                    if total_score > 0.1:
                        memory["_score"] = total_score
                        results.append(memory)

                except Exception:
                    continue

        # Sort by score
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)

        return results[:limit]

    def get_recent(self, limit: int = 10, memory_type: str = None) -> List[Dict]:
        """Get recent memories"""
        results = []

        dirs = [self.episodic_dir, self.semantic_dir]
        if memory_type == "working":
            dirs = [self.working_dir]

        for memory_dir in dirs:
            for path in sorted(
                memory_dir.glob("*.json"), key=lambda p: -p.stat().st_mtime
            ):
                try:
                    results.append(json.loads(path.read_text()))
                    if len(results) >= limit:
                        break
                except:
                    continue
            if len(results) >= limit:
                break

        return results[:limit]

    def get_user_profile(self) -> Dict:
        """Get aggregated user profile from memory"""
        profile = {
            "preferences": [],
            "facts": [],
            "recent_topics": [],
            "communication_style": "conversational",
        }

        # Get semantic memories
        for path in self.semantic_dir.glob("*.json"):
            try:
                mem = json.loads(path.read_text())
                if mem.get("category") == "preference":
                    profile["preferences"].append(mem["content"])
                elif mem.get("category") == "fact":
                    profile["facts"].append(mem["content"])
            except:
                continue

        # Get recent topics
        recent = self.get_recent(limit=20)
        topics = set()
        for mem in recent:
            topics.add(mem.get("category", "general"))
        profile["recent_topics"] = list(topics)

        return profile

    def get_context(self, query: str = None, max_memories: int = 10) -> str:
        """Get context string for LLM - recent memories + relevant to query"""
        context_parts = []

        # Recent memories
        recent = self.get_recent(limit=max_memories)
        if recent:
            context_parts.append("RECENT MEMORIES:")
            for mem in recent[:5]:
                cat = mem.get("category", "general")
                cont = mem.get("content", "")[:150]
                context_parts.append(f"- [{cat}] {cont}")

        # Query-relevant memories
        if query:
            relevant = self.search(query, limit=5)
            if relevant:
                context_parts.append(f"\nRELEVANT TO '{query}':")
                for mem in relevant:
                    cont = mem.get("content", "")[:150]
                    context_parts.append(f"- {cont}")

        return "\n".join(context_parts) if context_parts else ""

    def remember_preference(self, key: str, value: str) -> None:
        """Remember a user preference"""
        self.add(
            content=f"User preference: {key} = {value}",
            memory_type="semantic",
            importance=0.8,
            metadata={"key": key, "value": value, "category": "preference"},
        )

    def get_preference(self, key: str) -> Optional[str]:
        """Get a user preference"""
        results = self.search(f"preference {key}", limit=3)
        for mem in results:
            if mem.get("metadata", {}).get("key") == key:
                return mem.get("metadata", {}).get("value")
        return None

    def stats(self) -> Dict:
        """Get memory statistics"""
        return {
            "episodic": len(list(self.episodic_dir.glob("*.json"))),
            "semantic": len(list(self.semantic_dir.glob("*.json"))),
            "working": len(list(self.working_dir.glob("*.json"))),
            "current_session": self.session_id,
        }


# Global memory hub
_memory_hub: Optional[SOV3MemoryHub] = None


def get_memory_hub() -> SOV3MemoryHub:
    global _memory_hub
    if _memory_hub is None:
        _memory_hub = SOV3MemoryHub()
    return _memory_hub


# Integration with Jarvis
def add_to_memory(
    content: str, memory_type: str = "episodic", importance: float = 0.5
) -> str:
    """Quick add to memory"""
    return get_memory_hub().add(content, memory_type, importance)


def recall(query: str, limit: int = 5) -> List[Dict]:
    """Quick recall from memory"""
    return get_memory_hub().search(query, limit)


if __name__ == "__main__":
    # Test
    hub = get_memory_hub()

    # Add some memories
    hub.add("User prefers to be called Sir", memory_type="semantic", importance=0.9)
    hub.add("User is working on AI agent integration", memory_type="episodic")
    hub.add("User likes concise responses", memory_type="semantic", importance=0.8)

    # Search
    results = hub.search("AI")
    print(f"Found {len(results)} memories")
    for r in results:
        print(f"  - {r.get('content', '')[:80]}...")

    # Get context
    ctx = hub.get_context("preferences")
    print(f"\nContext:\n{ctx}")

    print(f"\nStats: {hub.stats()}")
