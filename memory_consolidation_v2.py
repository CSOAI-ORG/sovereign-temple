#!/usr/bin/env python3
"""
Memory Consolidation - Better Memory for Jarvis
Prioritizes important memories, summarizes conversations, creates anchors
"""

import time
import json
from typing import Dict, List, Optional
from collections import OrderedDict


class MemoryConsolidator:
    """Consolidate and prioritize memories"""

    def __init__(self):
        self.importance_keywords = {
            "high": [
                "important",
                "remember",
                "don't forget",
                "todo",
                "task",
                "meeting",
                "deadline",
                "project",
            ],
            "medium": [
                "preference",
                "like",
                "don't like",
                "habit",
                "routine",
                "often",
                "usually",
            ],
            "low": ["mention", "talked", "discussed", "casual"],
        }
        self.topic_keywords = {
            "work": ["project", "code", "meeting", "client", "deadline", "task"],
            "personal": ["family", "friend", "health", "exercise", "hobby"],
            "technical": ["python", "api", "server", "model", "ai", "llm"],
            "preferences": ["prefer", "like", "hate", "want", "need", "wish"],
        }
        self.anchor_memories = {}  # Persistent important memories
        self.session_summaries = []
        self.max_summaries = 10

    def assess_importance(self, text: str) -> float:
        """Assess how important a memory is (0-1)"""
        lower = text.lower()
        score = 0.3  # Base importance

        for keyword in self.importance_keywords["high"]:
            if keyword in lower:
                score += 0.3

        for keyword in self.importance_keywords["medium"]:
            if keyword in lower:
                score += 0.15

        return min(score, 1.0)

    def extract_topics(self, text: str) -> List[str]:
        """Extract topics from text"""
        lower = text.lower()
        topics = []

        for topic, keywords in self.topic_keywords.items():
            if any(k in lower for k in keywords):
                topics.append(topic)

        return topics if topics else ["general"]

    def consolidate(self, text: str, context: str = "") -> Dict:
        """Consolidate a memory"""
        importance = self.assess_importance(text)
        topics = self.extract_topics(text)

        memory = {
            "text": text,
            "context": context,
            "importance": importance,
            "topics": topics,
            "timestamp": time.time(),
            "consolidated": True,
        }

        # High importance = anchor memory
        if importance >= 0.7:
            key = f"anchor_{len(self.anchor_memories)}"
            self.anchor_memories[key] = memory
            memory["is_anchor"] = True

        return memory

    def create_session_summary(self, messages: List[Dict]) -> str:
        """Summarize conversation session"""
        if not messages:
            return ""

        # Extract key points
        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        assistant_msgs = [
            m["content"] for m in messages if m.get("role") == "assistant"
        ]

        summary = f"Session with {len(user_msgs)} user messages. "

        if user_msgs:
            # First message is usually the main topic
            summary += f"Started discussing: {user_msgs[0][:100]}. "

        if len(user_msgs) > 3:
            summary += f"Covered {len(set(user_msgs))} topics. "

        # Store summary
        self.session_summaries.append(
            {
                "summary": summary,
                "timestamp": time.time(),
                "message_count": len(messages),
            }
        )

        if len(self.session_summaries) > self.max_summaries:
            self.session_summaries = self.session_summaries[-self.max_summaries :]

        return summary

    def get_important_memories(self, limit: int = 5) -> List[Dict]:
        """Get most important memories"""
        anchors = list(self.anchor_memories.values())
        anchors.sort(key=lambda x: x.get("importance", 0), reverse=True)
        return anchors[:limit]

    def get_recent_topics(self) -> List[str]:
        """Get recently discussed topics"""
        topics = []
        for summary in self.session_summaries[-5:]:
            # Simplified topic extraction
            topics.extend(summary.get("topics", []))
        return list(set(topics))[-10:]


# User Preference Learning
class PreferenceLearner:
    """Learn user preferences over time"""

    def __init__(self):
        self.preferences = {
            "communication": {},  # how they want to be addressed
            "topics": {},  # interests
            "tasks": {},  # common tasks
            "schedule": {},  # when they're active
        }
        self.learned = {}

    def learn(self, text: str, response: str):
        """Learn from interaction"""
        lower = text.lower()

        # Communication preferences
        if any(w in lower for w in ["call me", "address me"]):
            # Extract name/preference
            pass

        # Time-based patterns
        hour = time.localtime().tm_hour
        if hour not in self.preferences["schedule"]:
            self.preferences["schedule"][hour] = 0
        self.preferences["schedule"][hour] += 1

    def get_preference(self, category: str, key: str) -> Optional[str]:
        """Get learned preference"""
        return self.learned.get(f"{category}:{key}")

    def set_preference(self, category: str, key: str, value: str):
        """Set a preference"""
        self.learned[f"{category}:{key}"] = value

    def get_peak_hours(self) -> List[int]:
        """Get user's most active hours"""
        schedule = self.preferences["schedule"]
        if not schedule:
            return []

        avg = sum(schedule.values()) / len(schedule)
        return [h for h, c in schedule.items() if c > avg]


# Global instances
_memory_consolidator = MemoryConsolidator()
_preference_learner = PreferenceLearner()


def get_consolidator() -> MemoryConsolidator:
    return _memory_consolidator


def get_preference_learner() -> PreferenceLearner:
    return _preference_learner


# Quick functions
def remember_important(text: str, context: str = "") -> str:
    """Remember something important"""
    result = _memory_consolidator.consolidate(text, context)
    if result.get("is_anchor"):
        return f"I'll remember that, Sir. It's important."
    return "Got it, Sir."


def what_do_you_remember() -> str:
    """What does Jarvis remember"""
    memories = _memory_consolidator.get_important_memories(3)
    if not memories:
        return "I don't have any important memories yet, Sir."

    lines = ["Here's what I've stored as important, Sir:"]
    for m in memories:
        lines.append(f"• {m['text'][:100]}...")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test
    print("Testing memory consolidation...")

    consolidator = MemoryConsolidator()

    # Test importance assessment
    test_texts = [
        "Don't forget to call John tomorrow",
        "I usually prefer coffee in the morning",
        "We talked about the weather",
    ]

    for text in test_texts:
        result = consolidator.consolidate(text)
        print(f"'{text[:40]}...' -> importance: {result['importance']}")

    print("Memory consolidation ready!")
