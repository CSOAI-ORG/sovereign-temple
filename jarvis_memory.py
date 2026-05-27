#!/usr/bin/env python3
"""
JARVIS Memory - Persistent conversation memory
Stores conversations, learns from interactions, maintains context
"""

import json
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

MEMORY_DIR = Path("/Users/nicholas/clawd/sovereign-temple-live/jarvis-memory")
MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class JARVISMemory:
    """Persistent memory for JARVIS"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.conversations_file = MEMORY_DIR / f"conversations_{user_id}.json"
        self.facts_file = MEMORY_DIR / f"facts_{user_id}.json"
        self.preferences_file = MEMORY_DIR / f"preferences_{user_id}.json"

        self.conversations = self._load_json(self.conversations_file, [])
        self.facts = self._load_json(self.facts_file, {})
        self.preferences = self._load_json(self.preferences_file, {})

    def _load_json(self, path: Path, default):
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except:
                return default
        return default

    def _save_json(self, path: Path, data):
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to conversation history"""
        self.conversations.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
        )

        # Keep last 1000 messages
        if len(self.conversations) > 1000:
            self.conversations = self.conversations[-1000:]

        self._save_json(self.conversations_file, self.conversations)

        # Extract facts from user messages
        if role == "user":
            self._extract_facts(content)

    def _extract_facts(self, text: str):
        """Simple fact extraction - learns from conversation"""
        # Look for patterns like "I like X" or "My name is Y"
        lower = text.lower()

        # Extract preferences
        if "i like" in lower:
            like = lower.split("i like")[1].split(".")[0].strip()
            self.facts["likes"] = self.facts.get("likes", [])
            if like not in self.facts["likes"]:
                self.facts["likes"].append(like)

        if "i hate" in lower:
            hate = lower.split("i hate")[1].split(".")[0].strip()
            self.facts["dislikes"] = self.facts.get("dislikes", [])
            if hate not in self.facts["dislikes"]:
                self.facts["dislikes"].append(hate)

        if "my name is" in lower:
            name = lower.split("my name is")[1].split()[0].strip()
            self.facts["name"] = name

        if "i'm " in lower or "i am " in lower:
            info = (
                lower.split("i'm ")[1].split()[0]
                if "i'm " in lower
                else lower.split("i am ")[1].split()[0]
            )
            if info not in ["a", "the", "here", "going"]:
                self.facts["about_me"] = info

        self._save_json(self.facts_file, self.facts)

    def get_context(self, max_messages: int = 10) -> str:
        """Get recent conversation context"""
        recent = self.conversations[-max_messages:]
        return "\n".join([f"{m['role']}: {m['content']}" for m in recent])

    def get_facts(self) -> Dict:
        """Get learned facts about user"""
        return self.facts

    def get_preference(self, key: str, default=None):
        """Get user preference"""
        return self.preferences.get(key, default)

    def set_preference(self, key: str, value):
        """Set user preference"""
        self.preferences[key] = value
        self._save_json(self.preferences_file, self.preferences)

    def search(self, query: str) -> List[Dict]:
        """Search conversation history"""
        query_lower = query.lower()
        results = []
        for msg in self.conversations:
            if query_lower in msg["content"].lower():
                results.append(msg)
        return results[-10:]  # Last 10 matches

    def clear(self):
        """Clear all memory"""
        self.conversations = []
        self.facts = {}
        self.preferences = {}
        self._save_json(self.conversations_file, [])
        self._save_json(self.facts_file, {})
        self._save_json(self.preferences_file, {})


# Global instance
memory = JARVISMemory()


def add_to_memory(role: str, content: str, metadata: Dict = None):
    """Add message to memory"""
    memory.add_message(role, content, metadata)


def get_memory_context() -> str:
    """Get conversation context for LLM"""
    return memory.get_context()


def get_user_facts() -> Dict:
    """Get learned facts about user"""
    return memory.get_facts()


def learn_from_user(message: str):
    """Extract and learn from user message"""
    memory.add_message("user", message)


def remember_assistant(response: str):
    """Remember assistant response"""
    memory.add_message("assistant", response)


if __name__ == "__main__":
    # Test memory
    print("Testing JARVIS Memory...")

    add_to_memory("user", "I like coding in Python")
    add_to_memory("user", "My name is Nicholas")
    add_to_memory("user", "I hate spam emails")

    print(f"Context: {get_memory_context()}")
    print(f"Facts: {get_user_facts()}")
    print(f"Search 'Python': {memory.search('Python')}")
