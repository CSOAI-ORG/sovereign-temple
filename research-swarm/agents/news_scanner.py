#!/usr/bin/env python3
"""News & Hacker News Scanner Agent

Monitors Hacker News, Reddit, Twitter for AI-related discussions.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from typing import Any, Dict, List


class HNScanner:
    """Scans Hacker News for AI-related stories."""

    HN_API = "https://hacker-news.firebaseio.com/v0"

    def get_top_stories(self, limit: int = 50) -> List[int]:
        """Get top story IDs."""
        url = f"{self.HN_API}/topstories.json"
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read())[:limit]

    def get_story(self, story_id: int) -> Dict[str, Any]:
        """Get story details."""
        url = f"{self.HN_API}/item/{story_id}.json"
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read())

    def scan_ai_stories(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Scan for AI-related stories."""
        keywords = keywords or [
            "llm", "ai", "language model", "gpt", "claude",
            "openai", "anthropic", "routing", "orchestration",
            "prompt injection", "jailbreak", "ai safety",
        ]

        story_ids = self.get_top_stories(100)
        matches = []

        for sid in story_ids:
            try:
                story = self.get_story(sid)
                title = story.get("title", "").lower()
                text = story.get("text", "").lower()
                combined = title + " " + text

                if any(kw in combined for kw in keywords):
                    matches.append({
                        "id": sid,
                        "title": story.get("title", ""),
                        "url": story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                        "score": story.get("score", 0),
                        "comments": story.get("descendants", 0),
                        "time": datetime.fromtimestamp(story.get("time", 0)).isoformat(),
                    })
            except Exception:
                continue

        return sorted(matches, key=lambda x: x["score"], reverse=True)


def main():
    scanner = HNScanner()
    stories = scanner.scan_ai_stories()

    print(f"Found {len(stories)} AI-related stories on HN:")
    for s in stories[:15]:
        print(f"  [{s['score']} pts, {s['comments']} comments] {s['title']}")
        print(f"    {s['url']}")
        print()


if __name__ == "__main__":
    main()
