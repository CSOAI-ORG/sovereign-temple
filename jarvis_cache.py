#!/usr/bin/env python3
"""
JARVIS Redis Cache - Caching layer for fast responses
Redis integration for rate limiting, caching, and queues
"""

import os
import json
import time
from typing import Optional, Any

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class JARVISCache:
    """Redis cache for JARVIS"""

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port

        if REDIS_AVAILABLE:
            try:
                self.client = redis.Redis(host=host, port=port, decode_responses=True)
                self.client.ping()
                self.connected = True
            except:
                self.connected = False
                self.client = None
        else:
            self.connected = False
            self.client = None

    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.connected:
            return None
        try:
            return self.client.get(key)
        except:
            return None

    def set(self, key: str, value: Any, expire: int = 3600):
        """Set value in cache"""
        if not self.connected:
            return False
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            self.client.setex(key, expire, value)
            return True
        except:
            return False

    def delete(self, key: str):
        """Delete key"""
        if self.connected:
            try:
                self.client.delete(key)
            except:
                pass

    def rate_limit(self, key: str, limit: int = 100, window: int = 60) -> bool:
        """Rate limiting"""
        if not self.connected:
            return True

        try:
            current = self.client.get(f"ratelimit:{key}")
            if current is None:
                self.client.setex(f"ratelimit:{key}", window, 1)
                return True

            if int(current) >= limit:
                return False

            self.client.incr(f"ratelimit:{key}")
            return True
        except:
            return True

    def push_queue(self, queue: str, message: Any):
        """Push to queue"""
        if not self.connected:
            return False
        try:
            if isinstance(message, (dict, list)):
                message = json.dumps(message)
            self.client.lpush(queue, message)
            return True
        except:
            return False

    def pop_queue(self, queue: str, timeout: int = 0) -> Optional[str]:
        """Pop from queue"""
        if not self.connected:
            return None
        try:
            if timeout > 0:
                result = self.client.brpop(queue, timeout)
                return result[1] if result else None
            else:
                return self.client.rpop(queue)
        except:
            return None


# Global instance
cache = JARVISCache()


def cache_get(key: str) -> Optional[str]:
    return cache.get(key)


def cache_set(key: str, value: Any, expire: int = 3600) -> bool:
    return cache.set(key, value, expire)


def check_rate_limit(client_id: str, limit: int = 100) -> bool:
    return cache.rate_limit(client_id, limit)


if __name__ == "__main__":
    print(f"Redis connected: {cache.connected}")
    if cache.connected:
        # Test
        cache.set("test_key", "test_value", 60)
        print(f"Get test: {cache.get('test_key')}")
        print(f"Rate limit: {cache.rate_limit('test_client')}")
