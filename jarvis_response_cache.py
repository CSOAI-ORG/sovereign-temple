#!/usr/bin/env python3
"""
JARVIS Response Cache - Smart caching for MCP responses
- Cache LLM responses
- Cache tool results
- Invalidate based on time
- Hash-based cache keys
"""

import hashlib
import json
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta


class ResponseCache:
    """Smart response caching"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl  # seconds
        self.cache: Dict[str, Dict] = {}
        self.stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _make_key(self, tool: str, arguments: dict) -> str:
        """Create cache key from tool and arguments"""
        key_data = f"{tool}:{json.dumps(arguments, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def get(self, tool: str, arguments: dict) -> Optional[Any]:
        """Get cached response"""
        key = self._make_key(tool, arguments)

        if key in self.cache:
            entry = self.cache[key]

            # Check TTL
            if time.time() - entry["timestamp"] < self.ttl:
                self.stats["hits"] += 1
                return entry["result"]
            else:
                # Expired
                del self.cache[key]

        self.stats["misses"] += 1
        return None

    def set(self, tool: str, arguments: dict, result: Any):
        """Cache a response"""
        key = self._make_key(tool, arguments)

        # Evict if full
        if len(self.cache) >= self.max_size:
            # Remove oldest
            oldest = min(self.cache.items(), key=lambda x: x[1]["timestamp"])
            del self.cache[oldest[0]]
            self.stats["evictions"] += 1

        self.cache[key] = {"result": result, "timestamp": time.time(), "tool": tool}

    def invalidate(self, tool: str = None):
        """Invalidate cache"""
        if tool:
            # Remove specific tool
            self.cache = {k: v for k, v in self.cache.items() if v["tool"] != tool}
        else:
            # Clear all
            self.cache = {}

    def get_stats(self) -> Dict:
        """Get cache stats"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0

        return {**self.stats, "size": len(self.cache), "hit_rate": f"{hit_rate:.1f}%"}

    def should_cache(self, tool: str) -> bool:
        """Check if tool result should be cached"""
        # Don't cache these tools
        no_cache = {
            "run_command",
            "execute_code",
            "capture_screenshot",
            "analyze_screenshot",
            "transcribe",
            "speak",
            "set_reminder",
            "create_agent",
            "delegate_task",
            "cache_set",
            "run_tests",
        }
        return tool not in no_cache


# Global cache
response_cache = ResponseCache()


def cache_get(tool: str, arguments: dict) -> Optional[Any]:
    return response_cache.get(tool, arguments)


def cache_set(tool: str, arguments: dict, result: Any):
    if response_cache.should_cache(tool):
        response_cache.set(tool, arguments, result)


def cache_stats() -> Dict:
    return response_cache.get_stats()


if __name__ == "__main__":
    print("Response Cache ready")

    # Test
    cache_set("test_tool", {"arg": "value"}, "cached_result")
    result = cache_get("test_tool", {"arg": "value"})
    print(f"Test: {result}")
    print(f"Stats: {cache_stats()}")
