#!/usr/bin/env python3
"""
DeepSeek-style aggressive context manager for Legion.
Source: DeepSeek published system card (not a leak — public documentation).

Strategy when tokens > threshold:
  Keep:     system message + latest tool round (last 2 messages)
  Discard:  everything else
"""

import time
from typing import Dict, List, Optional


class ContextManager:
    """
    Keeps context within model limits by aggressively truncating
    when the threshold is crossed.
    """

    def __init__(self, threshold: int = 98304):  # 96K tokens
        self.threshold = threshold
        self._system: Optional[Dict] = None
        self._messages: List[Dict] = []
        self.discarded = 0

    # ─── Public API ──────────────────────────────────────────────────────────

    def set_system(self, content: str):
        self._system = {"role": "system", "content": content}

    def add(self, role: str, content: str, tool_call: bool = False) -> int:
        """Add a message. Returns current token estimate."""
        msg = {"role": role, "content": content}
        if tool_call:
            msg["_tool"] = True
        self._messages.append(msg)
        tokens = self._estimate_tokens()
        if tokens >= self.threshold:
            self._truncate()
        return self._estimate_tokens()

    def window(self) -> List[Dict]:
        """Return the current valid context window."""
        out = []
        if self._system:
            out.append({"role": self._system["role"], "content": self._system["content"]})
        for m in self._messages:
            out.append({"role": m["role"], "content": m["content"]})
        return out

    @property
    def stats(self) -> Dict:
        return {
            "tokens": self._estimate_tokens(),
            "threshold": self.threshold,
            "messages": len(self._messages),
            "discarded": self.discarded,
        }

    # ─── Internal ────────────────────────────────────────────────────────────

    def _truncate(self):
        """Keep only the last 2 messages (latest tool round)."""
        keep = self._messages[-2:] if len(self._messages) >= 2 else self._messages[:]
        self.discarded += len(self._messages) - len(keep)
        self._messages = keep

    def _estimate_tokens(self) -> int:
        total = len(self._system["content"]) // 4 if self._system else 0
        for m in self._messages:
            total += len(m.get("content", "")) // 4
        return total


class LegionContextRouter:
    """
    Routes long-document queries through chunked processing
    with DeepSeek-style truncation between chunks.
    """

    def __init__(self):
        # One context manager per heavy node
        self.managers: Dict[str, ContextManager] = {
            "chronus":     ContextManager(threshold=98304),   # Archive RTX 8000
            "hephaestus":  ContextManager(threshold=98304),   # Forge RTX 8000
            "archimedes":  ContextManager(threshold=131072),  # A6000 (when online)
        }

    def process_document(
        self,
        document: str,
        query: str,
        node: str = "chronus",
        chunk_tokens: int = 80_000,
        overlap_chars: int = 2_000,
    ) -> str:
        """
        Break a large document into chunks, process each with truncation,
        then synthesise. Falls back to 'chronus' if node unknown.
        """
        mgr = self.managers.get(node, self.managers["chronus"])
        mgr.set_system(
            "You are a document analyst. Previous context may have been truncated "
            "for efficiency. Focus on the current segment and the query."
        )

        chunks = self._chunk(document, chunk_tokens * 4, overlap_chars)
        results = []

        for i, chunk in enumerate(chunks):
            tokens_used = mgr.add(
                "user",
                f"[Segment {i+1}/{len(chunks)}]\n{chunk}\n\nQuery: {query}",
                tool_call=True,
            )
            # In production this calls Ollama; here we return stats for testing
            results.append(
                f"[Segment {i+1} — {tokens_used} tokens, "
                f"{mgr.stats['discarded']} discarded so far]"
            )

        return self._synthesise(results, query)

    @staticmethod
    def _chunk(text: str, chunk_chars: int, overlap: int) -> List[str]:
        chunks, start = [], 0
        while start < len(text):
            chunks.append(text[start : start + chunk_chars])
            start += chunk_chars - overlap
        return chunks

    @staticmethod
    def _synthesise(parts: List[str], query: str) -> str:
        header = f"=== Combined analysis ({len(parts)} segments) for: {query} ==="
        return header + "\n" + "\n---\n".join(parts)


if __name__ == "__main__":
    mgr = ContextManager(threshold=200)  # tiny threshold for demo
    mgr.set_system("You are an AI assistant.")
    mgr.add("user", "Hello! " * 30)
    mgr.add("assistant", "Hi there! " * 30)
    mgr.add("user", "What can you do? " * 30)
    mgr.add("assistant", "Lots of things! " * 30)
    mgr.add("user", "Tell me more. " * 30)

    print("Stats:", mgr.stats)
    print("Window messages:", len(mgr.window()))
    print("Discarded:", mgr.discarded)
