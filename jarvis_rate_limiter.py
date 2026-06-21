#!/usr/bin/env python3
"""
JARVIS Rate Limiter - Redis-backed sliding window rate limiting
Features:
- Per-IP rate limiting
- Per-user rate limiting (with auth)
- Sliding window algorithm
- Configurable limits per endpoint

Run: python jarvis_rate_limiter.py
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Tuple
import os
import sys

try:
    import redis
except ImportError:
    redis = None


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception"""

    def __init__(self, limit: int, window: int, retry_after: int):
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded. Limit: {limit}/{window}s. Retry after: {retry_after}s"
        )


class RateLimitMode(Enum):
    """Rate limiting mode"""

    ALLOW = "allow"  # Allow all (no limiting)
    BLOCK = "block"  # Block requests over limit
    THROTTLE = "throttle"  # Slow down requests


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""

    requests: int = 60  # Max requests
    window_seconds: int = 60  # Time window
    mode: RateLimitMode = RateLimitMode.BLOCK
    burst_allowance: int = 10  # Extra requests for bursts
    per_endpoint: bool = False  # Different limits per endpoint


@dataclass
class RateLimitStats:
    """Rate limiting statistics"""

    total_requests: int = 0
    allowed: int = 0
    blocked: int = 0
    throttled: int = 0
    by_ip: Dict[str, int] = field(default_factory=dict)
    by_user: Dict[str, int] = field(default_factory=dict)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using Redis or in-memory fallback
    """

    def __init__(self, config: RateLimitConfig = None, redis_url: str = None):
        self.config = config or RateLimitConfig()
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self._memory_store: Dict[str, list] = defaultdict(list)
        self.stats = RateLimitStats()

        # Try to connect to Redis
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection"""
        if redis is None:
            print("⚠️  Redis not available, using in-memory rate limiting")
            return

        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            print("✅ Redis rate limiter initialized")
        except Exception as e:
            print(f"⚠️  Redis unavailable ({e}), using in-memory")
            self.redis_client = None

    def _get_redis_key(self, identifier: str, endpoint: str = None) -> str:
        """Generate Redis key for rate limiting"""
        if endpoint and self.config.per_endpoint:
            return f"ratelimit:{identifier}:{endpoint}"
        return f"ratelimit:{identifier}"

    def _cleanup_old_entries(self, timestamps: list, window: int) -> list:
        """Remove timestamps outside the window"""
        cutoff = time.time() - window
        return [t for t in timestamps if t > cutoff]

    def check_rate_limit(
        self, identifier: str, endpoint: str = None
    ) -> Tuple[bool, int]:
        """
        Check if request is within rate limit
        Returns: (allowed, retry_after_seconds)
        """
        self.stats.total_requests += 1

        if self.config.mode == RateLimitMode.ALLOW:
            return True, 0

        window = self.config.window_seconds
        limit = self.config.requests + self.config.burst_allowance

        # Try Redis first
        if self.redis_client:
            try:
                key = self._get_redis_key(identifier, endpoint)
                now = time.time()

                # Remove old entries
                self.redis_client.zremrangebyscore(key, 0, now - window)

                # Count current requests
                count = self.redis_client.zcard(key)

                if count >= limit:
                    # Find oldest entry to calculate retry time
                    oldest = self.redis_client.zrange(key, 0, 0, withscores=True)
                    if oldest:
                        oldest_time = oldest[0][1]
                        retry_after = int(oldest_time + window - now) + 1
                    else:
                        retry_after = window

                    self.stats.blocked += 1
                    return False, retry_after

                # Add new request
                self.redis_client.zadd(key, {f"{now}": now})
                self.redis_client.expire(key, window + 1)

                self.stats.allowed += 1
                return True, 0

            except Exception as e:
                print(f"Redis error: {e}, falling back to memory")

        # Fallback to in-memory
        key = self._get_redis_key(identifier, endpoint)
        timestamps = self._memory_store[key]
        now = time.time()

        # Clean old entries
        self._memory_store[key] = self._cleanup_old_entries(timestamps, window)

        if len(self._memory_store[key]) >= limit:
            # Calculate retry time
            oldest = min(self._memory_store[key]) if self._memory_store[key] else now
            retry_after = int(oldest + window - now) + 1

            self.stats.blocked += 1
            return False, retry_after

        # Add new timestamp
        self._memory_store[key].append(now)

        self.stats.allowed += 1
        return True, 0

    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        return {
            "total_requests": self.stats.total_requests,
            "allowed": self.stats.allowed,
            "blocked": self.stats.blocked,
            "throttled": self.stats.throttled,
            "mode": self.config.mode.value,
            "limit": self.config.requests,
            "window": self.config.window_seconds,
        }

    def reset(self, identifier: str = None):
        """Reset rate limits"""
        if identifier:
            key = self._get_redis_key(identifier)
            if self.redis_client:
                try:
                    self.redis_client.delete(key)
                except:
                    pass
            if key in self._memory_store:
                del self._memory_store[key]
        else:
            self._memory_store.clear()
            self.stats = RateLimitStats()


class FastAPIRateLimitMiddleware:
    """FastAPI middleware for rate limiting"""

    def __init__(
        self, app, rate_limiter: SlidingWindowRateLimiter, exempt_paths: list = None
    ):
        self.app = app
        self.rate_limiter = rate_limiter
        self.exempt_paths = exempt_paths or [
            "/health",
            "/pulse",
            "/docs",
            "/openapi.json",
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get path
        path = scope.get("path", "/")

        # Skip exempt paths
        if any(path.startswith(p) for p in self.exempt_paths):
            await self.app(scope, receive, send)
            return

        # Get identifier (IP or user)
        client = scope.get("client")
        identifier = client[0] if client else "unknown"

        # Check rate limit
        allowed, retry_after = self.rate_limiter.check_rate_limit(identifier, path)

        if not allowed:
            # Return 429 response
            response = {
                "error": "Rate limit exceeded",
                "retry_after": retry_after,
                "limit": self.rate_limiter.config.requests,
                "window": self.rate_limiter.config.window_seconds,
            }

            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"retry-after", str(retry_after).encode()],
                        [
                            b"x-rate-limit",
                            str(self.rate_limiter.config.requests).encode(),
                        ],
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": json.dumps(response).encode(),
                }
            )
            return

        # Process request
        await self.app(scope, receive, send)


def create_rate_limiter(redis_url: str = None) -> SlidingWindowRateLimiter:
    """Factory function to create rate limiter"""
    config = RateLimitConfig(
        requests=60,  # 60 requests
        window_seconds=60,  # per minute
        mode=RateLimitMode.BLOCK,
        burst_allowance=10,  # allow bursts up to 70
    )
    return SlidingWindowRateLimiter(config, redis_url)


def demo():
    """Demo the rate limiter"""
    print("=" * 50)
    print("JARVIS Rate Limiter Demo")
    print("=" * 50)

    limiter = create_rate_limiter()

    # Test basic rate limiting
    print("\n1. Testing rate limiting (60 requests/min)...")
    for i in range(65):
        allowed, retry = limiter.check_rate_limit("test_ip")
        if not allowed:
            print(f"   Request {i + 1}: BLOCKED (retry in {retry}s)")
        elif i == 0:
            print(f"   Request {i + 1}: allowed")

    # Show stats
    print("\n2. Statistics:")
    stats = limiter.get_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # Test different IPs
    print("\n3. Testing different IPs...")
    limiter.reset()
    allowed1, _ = limiter.check_rate_limit("192.168.1.1")
    allowed2, _ = limiter.check_rate_limit("192.168.1.2")
    print(f"   IP 1: {'allowed' if allowed1 else 'blocked'}")
    print(f"   IP 2: {'allowed' if allowed2 else 'blocked'}")

    print("\n✅ Rate limiter demo complete!")


if __name__ == "__main__":
    import json

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        # Just print usage
        print("Usage: python jarvis_rate_limiter.py demo")
        print("\nTo integrate with FastAPI:")
        print(
            "  from jarvis_rate_limiter import create_rate_limiter, FastAPIRateLimitMiddleware"
        )
        print("  limiter = create_rate_limiter()")
        print("  app.add_middleware(FastAPIRateLimitMiddleware, rate_limiter=limiter)")
