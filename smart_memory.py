#!/usr/bin/env python3
"""
Smart Memory System - Important memories stay front and accessible
Prioritizes important info, quick retrieval, no info buried
"""

import time
import json
from typing import Dict, List, Optional
from collections import OrderedDict


class SmartMemory:
    """
    Memory that keeps important things FRONT and ACCESSIBLE
    - Anchor memories always at top
    - Recent important memories easily retrieved
    - No important info buried deep
    """

    def __init__(self):
        # PRIORITY 1: Anchors (most important, never buried)
        self.anchors = OrderedDict()  # key -> memory

        # PRIORITY 2: Recent important (last 20 important items)
        self.recent_important = OrderedDict()
        self.max_recent = 20

        # PRIORITY 3: Current session items
        self.session_items = []
        self.max_session = 50

        # All memories (with priority scores)
        self.all_memories = OrderedDict()

        # Importance keywords
        self.high_importance = [
            "remember",
            "important",
            "don't forget",
            "todo",
            "task",
            "meeting",
            "deadline",
            "project",
            "address",
            "name",
            "phone",
            "email",
            "password",
            "key",
            "critical",
            "essential",
            "never forget",
            "always",
            "must",
            "required",
        ]

        self.medium_importance = [
            "prefer",
            "like",
            "usually",
            "habit",
            "routine",
            "often",
            "sometimes",
            "occasionally",
        ]

        self.user_topics = set()  # Topics user cares about

    def add(
        self, text: str, source: str = "conversation", importance: float = None
    ) -> Dict:
        """Add memory - calculates importance automatically"""
        # Auto-assess importance if not provided
        if importance is None:
            importance = self._assess_importance(text)

        timestamp = time.time()
        memory_id = f"{timestamp}_{hash(text) % 10000}"

        memory = {
            "id": memory_id,
            "text": text,
            "importance": importance,
            "source": source,
            "timestamp": timestamp,
            "access_count": 0,
            "last_accessed": timestamp,
        }

        # Store in all
        self.all_memories[memory_id] = memory

        # PRIORITY PLACEMENT
        if importance >= 0.8:
            # HIGH importance -> ANCHORS (front, accessible)
            self.anchors[memory_id] = memory
            # Keep anchors limited
            if len(self.anchors) > 30:
                self.anchors.popitem(last=False)
        elif importance >= 0.5:
            # MEDIUM importance -> Recent important
            self.recent_important[memory_id] = memory
            # Keep recent limited
            if len(self.recent_important) > self.max_recent:
                self.recent_important.popitem(last=False)
        else:
            # LOW importance -> Session only
            self.session_items.append(memory)
            if len(self.session_items) > self.max_session:
                self.session_items = self.session_items[-self.max_session :]

        return memory

    def _assess_importance(self, text: str) -> float:
        """Auto-calculate importance 0-1"""
        lower = text.lower()
        score = 0.2  # Base

        # High importance keywords
        for kw in self.high_importance:
            if kw in lower:
                score += 0.4
                break

        # Medium importance
        for kw in self.medium_importance:
            if kw in lower:
                score += 0.2
                break

        # User topics (learned)
        for topic in self.user_topics:
            if topic in lower:
                score += 0.3
                break

        # Explicit markers
        if "!" in text or "IMPORTANT" in text.upper():
            score += 0.2

        # Length factor (longer = more context = potentially important)
        if len(text) > 50:
            score += 0.1

        return min(score, 1.0)

    def learn_topic(self, topic: str):
        """Learn what topics user cares about"""
        self.user_topics.add(topic.lower())

    def get(self, query: str = None, limit: int = 5) -> List[str]:
        """
        Get memories - IMPORTANT ONES FIRST
        No important memory buried!
        """
        results = []
        seen = set()

        # PRIORITY 1: Anchors first (always front)
        for mem in self.anchors.values():
            if query is None or self._matches(query, mem["text"]):
                if mem["id"] not in seen:
                    results.append(mem)
                    seen.add(mem["id"])
                    mem["access_count"] += 1
                    mem["last_accessed"] = time.time()

        # PRIORITY 2: Recent important
        for mem in self.recent_important.values():
            if query is None or self._matches(query, mem["text"]):
                if mem["id"] not in seen:
                    results.append(mem)
                    seen.add(mem["id"])
                    mem["access_count"] += 1
                    mem["last_accessed"] = time.time()

        # PRIORITY 3: Session items
        for mem in reversed(self.session_items):
            if query is None or self._matches(query, mem["text"]):
                if mem["id"] not in seen:
                    results.append(mem)
                    seen.add(mem["id"])
                    if len(results) >= limit:
                        break

        return results[:limit]

    def _matches(self, query: str, text: str) -> bool:
        """Check if query matches text"""
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        return bool(query_words & text_words)

    def recall(self, query: str) -> str:
        """Recall memories - IMPORTANT FIRST"""
        memories = self.get(query, limit=5)

        if not memories:
            return ""

        lines = []
        for mem in memories:
            prefix = (
                "⭐"
                if mem["importance"] >= 0.8
                else "📌"
                if mem["importance"] >= 0.5
                else "•"
            )
            lines.append(f"{prefix} {mem['text'][:150]}")

        return "\n".join(lines)

    def remember_important(self, text: str) -> str:
        """Explicitly remember something important"""
        self.add(text, source="explicit", importance=0.95)
        return f"I'll remember that, Sir. It's stored in my anchors."

    def what_do_you_remember(self) -> str:
        """What does Jarvis remember - IMPORTANT ONES FIRST"""
        return self.recall()

    def get_stats(self) -> Dict:
        """Memory stats"""
        high = len(self.anchors)
        medium = len(self.recent_important)
        low = len(self.session_items)

        return {
            "anchors": high,
            "recent_important": medium,
            "session": low,
            "total": high + medium + low,
        }


# Global instance
_smart_memory = None


def get_smart_memory() -> SmartMemory:
    global _smart_memory
    if _smart_memory is None:
        _smart_memory = SmartMemory()
    return _smart_memory


# Quick functions
def remember(text: str) -> str:
    """Remember something important"""
    return get_smart_memory().remember_important(text)


def recall(query: str = None) -> str:
    """Recall memories"""
    return get_smart_memory().recall(query)


# Test
if __name__ == "__main__":
    mem = get_smart_memory()

    # Add some test memories
    mem.add("Nick's phone is 555-0123", importance=0.95)
    mem.add("Meeting with client at 3pm tomorrow", importance=0.85)
    mem.add("The weather was nice today", importance=0.3)
    mem.add("Python is his favorite language", importance=0.6)
    mem.add("Don't forget to buy milk", importance=0.9)

    print("Memory test:")
    print(f"Stats: {mem.get_stats()}")
    print(f"\nRecall all:\n{mem.recall()}")
    print(f"\nSearch 'phone':\n{mem.recall('phone')}")
