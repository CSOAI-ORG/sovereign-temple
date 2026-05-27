#!/usr/bin/env python3
"""
JARVIS Improved Memory - Better recall and context
- Semantic memory search
- Importance weighting
- Time-based decay
- Better fact extraction
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
from datetime import datetime, timedelta


class ImprovedMemory:
    """Improved memory with better recall"""

    def __init__(
        self,
        storage_path: str = "/Users/nicholas/clawd/sovereign-temple-live/improved-memory",
    ):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Load existing memory
        self.conversations = self._load("conversations.json", [])
        self.facts = self._load("facts.json", {})
        self.entities = self._load("entities.json", {})
        self.interactions = self._load("interactions.json", [])

        # Track importance
        self.importance_scores = defaultdict(float)

    def _load(self, filename: str, default):
        path = self.storage_path / filename
        if path.exists():
            try:
                return json.loads(path.read_text())
            except:
                return default
        return default

    def _save(self, filename: str, data):
        (self.storage_path / filename).write_text(
            json.dumps(data, indent=2, default=str)
        )

    def add_message(self, role: str, content: str, importance: float = 1.0):
        """Add message with importance"""
        # Add timestamp
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "importance": importance,
            "tokens": len(content.split()),
        }

        self.conversations.append(entry)

        # Keep last 2000 messages
        if len(self.conversations) > 2000:
            self.conversations = self.conversations[-2000:]

        # Extract facts from user messages
        if role == "user":
            self._extract_facts(content)

        # Save
        self._save("conversations.json", self.conversations)

        return entry

    def _extract_facts(self, text: str):
        """Better fact extraction using patterns"""
        text_lower = text.lower()

        # Name patterns
        name_patterns = [
            r"my name is (\w+)",
            r"i'm (\w+)",
            r"call me (\w+)",
            r"i am (\w+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text_lower)
            if match:
                self.facts["name"] = match.group(1)

        # Preference patterns
        like_patterns = [
            r"i (?:really )?(?:like|love|adore) (.+?)(?:\.|,|!|$)",
            r"(?:my )?favorite (.+?) (?:is|are)",
        ]
        for pattern in like_patterns:
            for match in re.finditer(pattern, text_lower):
                like = match.group(1).strip()
                if len(like) < 50:
                    self.facts.setdefault("likes", []).append(like)

        # Dislike patterns
        hate_patterns = [
            r"i (?:hate|dislike|don't like) (.+?)(?:\.|,|!|$)",
            r"(?:my )?least favorite (.+?) (?:is|are)",
        ]
        for pattern in hate_patterns:
            for match in re.finditer(pattern, text_lower):
                hate = match.group(1).strip()
                if len(hate) < 50:
                    self.facts.setdefault("dislikes", []).append(hate)

        # Work/role patterns
        work_patterns = [
            r"i work (?:as|with|in) (.+?)(?:\.|,|!|$)",
            r"i'm a? (\w+) (?:at|for|in)",
        ]
        for pattern in work_patterns:
            match = re.search(pattern, text_lower)
            if match:
                self.facts["work"] = match.group(1)

        # Location patterns
        loc_patterns = [
            r"i (?:live|am) (?:in|at) (.+?)(?:\.|,|!|$)",
            r"(?:based|located) (?:in|at) (.+?)(?:\.|,|!|$)",
        ]
        for pattern in loc_patterns:
            match = re.search(pattern, text_lower)
            if match:
                self.facts["location"] = match.group(1)

        # Save facts
        self._save("facts.json", self.facts)

    def get_context(self, max_tokens: int = 4000) -> str:
        """Get context within token limit"""
        context_parts = []
        current_tokens = 0

        # Add most recent and important
        sorted_convo = sorted(
            self.conversations[-50:],  # Last 50
            key=lambda x: (
                x.get("importance", 1.0)
                * (1 + (time.time() - x.get("timestamp", 0)) / 86400)
            ),
            reverse=True,
        )

        for msg in reversed(sorted_convo):
            tokens = msg.get("tokens", len(msg["content"].split()))
            if current_tokens + tokens > max_tokens:
                break

            prefix = "User" if msg["role"] == "user" else "JARVIS"
            context_parts.append(f"{prefix}: {msg['content']}")
            current_tokens += tokens

        return "\n".join(context_parts[-20:])

    def get_facts(self) -> Dict:
        """Get all facts"""
        return {
            **self.facts,
            "conversation_count": len(self.conversations),
            "last_interaction": self.conversations[-1]["timestamp"]
            if self.conversations
            else None,
        }

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Improved search with relevance"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []

        for msg in self.conversations[-200:]:  # Search last 200
            content_lower = msg["content"].lower()

            # Calculate relevance score
            score = 0

            # Exact match
            if query_lower in content_lower:
                score += 10

            # Word overlap
            content_words = set(content_lower.split())
            overlap = len(query_words & content_words)
            score += overlap * 2

            # Recency boost
            age = (time.time() - msg.get("timestamp", 0)) / 86400
            score += max(0, 5 - age)

            # Importance boost
            score += msg.get("importance", 1.0) * 3

            if score > 3:
                results.append(
                    {
                        "content": msg["content"],
                        "role": msg["role"],
                        "score": score,
                        "timestamp": msg.get("timestamp"),
                    }
                )

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:max_results]

    def remember(self, fact: str, category: str = "general"):
        """Remember a specific fact"""
        if category not in self.facts:
            self.facts[category] = []

        if fact not in self.facts[category]:
            self.facts[category].append(fact)
            self._save("facts.json", self.facts)

        return {"status": "remembered", "fact": fact, "category": category}

    def get_summary(self) -> Dict:
        """Get memory summary"""
        return {
            "conversations": len(self.conversations),
            "facts": len(self.facts),
            "last_interaction": datetime.fromtimestamp(
                self.conversations[-1]["timestamp"]
            ).isoformat()
            if self.conversations
            else None,
        }


# Global instance
improved_memory = ImprovedMemory()


def add_message(role: str, content: str, importance: float = 1.0):
    return improved_memory.add_message(role, content, importance)


def get_memory_context(max_tokens: int = 4000) -> str:
    return improved_memory.get_context(max_tokens)


def get_user_facts() -> Dict:
    return improved_memory.get_facts()


def search_memory(query: str, max_results: int = 5) -> List[Dict]:
    return improved_memory.search(query, max_results)


def remember_fact(fact: str, category: str = "general") -> Dict:
    return improved_memory.remember(fact, category)


if __name__ == "__main__":
    print("Improved Memory ready")

    # Test
    add_message("user", "My name is Nicholas and I love coding")
    add_message("assistant", "Nice to meet you Nicholas!")

    print(f"Context: {get_memory_context()[:200]}...")
    print(f"Facts: {get_user_facts()}")
