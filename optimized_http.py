#!/usr/bin/env python3
"""
Optimized HTTP Client - Connection Pooling & Session Reuse
Use this instead of raw requests for all HTTP calls to Ollama/MCP servers
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import lru_cache
import hashlib
import json
import time
from typing import Optional, Dict, Any
import threading


class OptimizedHTTP:
    """Connection-pooled HTTP client with caching"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=50,
            max_retries=retry_strategy,
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._cache: Dict[str, tuple] = {}
        self._cache_lock = threading.Lock()
        self._max_cache_size = 500
        self._cache_ttl = 300

        self._initialized = True

    def get(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", 30)
        return self.session.get(url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", 60)
        return self.session.post(url, **kwargs)

    def cached_get(
        self, url: str, ttl: int = 60, **kwargs
    ) -> Optional[requests.Response]:
        cache_key = self._make_cache_key(url, None, kwargs)

        with self._cache_lock:
            if cache_key in self._cache:
                cached_time, cached_data = self._cache[cache_key]
                if time.time() - cached_time < ttl:
                    resp = requests.Response()
                    resp._content = cached_data
                    resp.status_code = 200
                    return resp

        kwargs.setdefault("timeout", 30)
        resp = self.session.get(url, **kwargs)

        if resp.status_code == 200:
            with self._cache_lock:
                if len(self._cache) > self._max_cache_size:
                    self._evict_oldest()
                self._cache[cache_key] = (time.time(), resp.content)

        return resp

    def _make_cache_key(self, url: str, method: Optional[str], params: Dict) -> str:
        key_data = f"{url}:{method}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _evict_oldest(self):
        if not self._cache:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
        del self._cache[oldest_key]

    def clear_cache(self):
        with self._cache_lock:
            self._cache.clear()


http_client = OptimizedHTTP()
HTTP_OPTIMIZED = True


def get_ollama_response(
    url: str, payload: Dict[str, Any], stream: bool = False
) -> Optional[Dict]:
    """Optimized Ollama API call with connection pooling"""
    try:
        resp = http_client.post(url, json=payload, stream=stream)

        if stream:
            return resp.iter_lines()

        return resp.json()
    except Exception as e:
        print(f"Ollama request failed: {e}")
        return None


def get_mcp_tools() -> int:
    """Get MCP tool count with caching"""
    try:
        resp = http_client.cached_get(
            "http://localhost:3101/mcp",
            ttl=30,
            headers={"Content-Type": "application/json"},
            data='{"jsonrpc":"2.0","id":1,"method":"tools/list"}',
        )
        if resp:
            data = resp.json()
            return len(data.get("result", {}).get("tools", []))
    except:
        pass
    return 0


async def async_post(
    url: str, payload: Dict[str, Any], timeout: int = 60
) -> Optional[Dict]:
    """Async version using httpx if available"""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=timeout)
            return resp.json()
    except ImportError:
        return None


if __name__ == "__main__":
    print("Testing optimized HTTP client...")

    resp = http_client.get("http://localhost:11436/api/tags")
    print(f"Ollama: {resp.json()['models'][0]['name']}")

    print(f"Cache size: {len(http_client._cache)}")
    print("✓ Optimized HTTP client ready")
