#!/usr/bin/env python3
"""
JARVIS Persistent Memory System
Survives restarts, wires to SOV3, maintains conversation context.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

MEMORY_DIR = Path("/Users/nicholas/clawd/jarvis-memory")
MEMORY_DIR.mkdir(exist_ok=True)
CONVERSATIONS_FILE = MEMORY_DIR / "conversations.json"
SESSION_FILE = MEMORY_DIR / "current_session.json"
SUMMARIES_FILE = MEMORY_DIR / "session_summaries.json"
MAX_CONVERSATIONS = 500
MAX_SESSION_LENGTH = 100  # messages before auto-summarize


class JarvisMemory:
    """Persistent conversation memory for JARVIS."""

    def __init__(self):
        self.conversations = self._load_json(CONVERSATIONS_FILE, [])
        self.current_session = self._load_json(
            SESSION_FILE, {"messages": [], "started_at": None, "topic": None}
        )
        self.summaries = self._load_json(SUMMARIES_FILE, [])
        self.message_count = len(self.current_session.get("messages", []))

    def _load_json(self, path, default):
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                return default
        return default

    def _save(self, path, data):
        path.write_text(json.dumps(data, indent=2, default=str))

    def add_message(self, role: str, content: str, emotion: str = "neutral"):
        """Add a message to the current session."""
        if self.current_session.get("started_at") is None:
            self.current_session["started_at"] = datetime.now(timezone.utc).isoformat()

        msg = {
            "role": role,
            "content": content,
            "emotion": emotion,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.current_session["messages"].append(msg)
        self.message_count += 1
        self._save(SESSION_FILE, self.current_session)

        # Auto-summarize if session too long
        if self.message_count >= MAX_SESSION_LENGTH:
            self._summarize_session()

    def get_recent_context(self, n: int = 10) -> List[Dict]:
        """Get recent messages for context window."""
        messages = self.current_session.get("messages", [])
        return messages[-n:]

    def get_topic_summary(self) -> str:
        """Get a summary of what the current conversation is about."""
        messages = self.current_session.get("messages", [])
        if not messages:
            return ""

        # Extract key topics from user messages
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        if not user_msgs:
            return ""

        # Simple topic extraction from first few user messages
        topics = []
        for msg in user_msgs[:5]:
            words = msg.lower().split()
            if len(words) > 3:
                topics.append(msg[:100])

        return " | ".join(topics[:3])

    def _summarize_session(self):
        """Summarize and archive the current session."""
        messages = self.current_session.get("messages", [])
        if not messages:
            return

        # Create summary
        user_msgs = [m for m in messages if m["role"] == "user"]
        jarvis_msgs = [m for m in messages if m["role"] == "assistant"]

        summary = {
            "started_at": self.current_session.get("started_at"),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(messages),
            "user_messages": len(user_msgs),
            "jarvis_messages": len(jarvis_msgs),
            "topics": self.get_topic_summary(),
            "emotions": list(set(m.get("emotion", "neutral") for m in user_msgs)),
            "first_user_msg": user_msgs[0]["content"][:200] if user_msgs else "",
            "last_user_msg": user_msgs[-1]["content"][:200] if user_msgs else "",
        }

        self.summaries.append(summary)
        self.conversations.append(
            {
                "session": self.current_session,
                "summary": summary,
            }
        )

        # Trim old conversations
        if len(self.conversations) > MAX_CONVERSATIONS:
            self.conversations = self.conversations[-MAX_CONVERSATIONS:]
        if len(self.summaries) > MAX_CONVERSATIONS:
            self.summaries = self.summaries[-MAX_CONVERSATIONS:]

        self._save(CONVERSATIONS_FILE, self.conversations)
        self._save(SUMMARIES_FILE, self.summaries)

        # Reset current session
        self.current_session = {"messages": [], "started_at": None, "topic": None}
        self.message_count = 0
        self._save(SESSION_FILE, self.current_session)

    def get_conversation_history(self, query: str = None, limit: int = 5) -> str:
        """Search past conversations for context."""
        if not query:
            return ""

        results = []
        query_lower = query.lower()

        for conv in reversed(self.conversations):
            summary = conv.get("summary", {})
            if (
                query_lower in summary.get("topics", "").lower()
                or query_lower in summary.get("first_user_msg", "").lower()
                or query_lower in summary.get("last_user_msg", "").lower()
            ):
                results.append(
                    f"- {summary.get('started_at', '')}: {summary.get('first_user_msg', '')[:150]}"
                )
                if len(results) >= limit:
                    break

        return "\n".join(results) if results else ""

    def flush(self):
        """Save current session on shutdown."""
        if self.current_session.get("messages"):
            self._summarize_session()


# Global instance
memory = JarvisMemory()
