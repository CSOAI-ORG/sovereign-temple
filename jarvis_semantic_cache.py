#!/usr/bin/env python3
"""
JARVIS Semantic Cache - Intelligent Response Caching
Features:
- Semantic similarity matching for cache hits
- TTL with access patterns
- Cache statistics and hit rate tracking
- Integration with existing memory system

Run: python jarvis_semantic_cache.py
"""

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import os
import sys

# Add paths for embedding
sys.path.insert(0, os.path.dirname(__file__))


@dataclass
class CacheEntry:
    """Cached response with metadata"""

    key: str
    request_hash: str
    response: str
    request_text: str
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl_seconds: float = 3600.0
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Embedder:
    """Simple hash-based embedding for fast similarity"""

    def __init__(self, dim: int = 384):
        self.dim = dim
        # Use a fixed seed for reproducibility
        np.random.seed(42)
        self.weights = np.random.randn(256, dim).astype(np.float32)

    def embed(self, text: str) -> np.ndarray:
        """Create embedding from text using word hashes"""
        words = text.lower().split()
        if not words:
            return np.zeros(self.dim, dtype=np.float32)

        # Hash each word to an index
        embeddings = []
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16) % 256
            embeddings.append(self.weights[h])

        # Average and normalize
        if embeddings:
            result = np.mean(embeddings, axis=0)
            result = result / (np.linalg.norm(result) + 1e-8)
            return result.astype(np.float32)

        return np.zeros(self.dim, dtype=np.float32)


class SemanticCache:
    """Cache with semantic similarity matching"""

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_entries: int = 1000,
        default_ttl: float = 3600.0,
        embedder: Optional[Embedder] = None,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.default_ttl = default_ttl

        self.embedder = embedder or Embedder()

        # Storage
        self.entries: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []  # For LRU

        # Stats
        self.stats = {"hits": 0, "misses": 0, "evictions": 0, "total_requests": 0}

    def _make_key(self, text: str, params: Dict = None) -> str:
        """Create cache key from request"""
        parts = [text]
        if params:
            parts.append(json.dumps(params, sort_keys=True))
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    def _make_request_hash(self, text: str, params: Dict = None) -> str:
        """Create request hash for similarity matching"""
        parts = [text.lower().strip()]
        if params:
            for k, v in sorted(params.items()):
                parts.append(f"{k}={v}")
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between embeddings"""
        if a is None or b is None:
            return 0.0
        return float(np.dot(a, b))

    def get(self, request: str, params: Dict = None) -> Optional[str]:
        """Get cached response if exists"""
        self.stats["total_requests"] += 1

        request_hash = self._make_request_hash(request, params)
        key = self._make_key(request, params)

        # Exact match
        if key in self.entries:
            entry = self.entries[key]
            if self._is_valid(entry):
                entry.last_accessed = time.time()
                entry.access_count += 1
                self._update_access_order(key)
                self.stats["hits"] += 1
                return entry.response

        # Semantic similarity search
        request_embedding = self.embedder.embed(request)

        best_match = None
        best_similarity = 0.0

        for k, entry in self.entries.items():
            if not self._is_valid(entry):
                continue

            if entry.embedding is not None:
                similarity = self._cosine_similarity(request_embedding, entry.embedding)
                if (
                    similarity > best_similarity
                    and similarity >= self.similarity_threshold
                ):
                    best_similarity = similarity
                    best_match = entry

        if best_match:
            best_match.last_accessed = time.time()
            best_match.access_count += 1
            self._update_access_order(best_match.key)
            self.stats["hits"] += 1
            return best_match.response

        self.stats["misses"] += 1
        return None

    def set(self, request: str, response: str, params: Dict = None, ttl: float = None):
        """Store response in cache"""
        key = self._make_key(request, params)

        # Evict if needed
        if len(self.entries) >= self.max_entries and key not in self.entries:
            self._evict_lru()

        embedding = self.embedder.embed(request)

        entry = CacheEntry(
            key=key,
            request_hash=self._make_request_hash(request, params),
            response=response,
            request_text=request[:200],
            created_at=time.time(),
            last_accessed=time.time(),
            ttl_seconds=ttl or self.default_ttl,
            embedding=embedding,
        )

        self.entries[key] = entry
        self._update_access_order(key)

    def _is_valid(self, entry: CacheEntry) -> bool:
        """Check if entry is still valid"""
        age = time.time() - entry.created_at
        return age < entry.ttl_seconds

    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self.access_order:
            return

        # Find oldest valid entry
        for key in self.access_order[:10]:
            if key in self.entries:
                del self.entries[key]
                self.access_order.remove(key)
                self.stats["evictions"] += 1
                return

    def _update_access_order(self, key: str):
        """Update access order for LRU"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    def invalidate(self, pattern: str = None):
        """Invalidate cache entries"""
        if pattern is None:
            self.entries.clear()
            self.access_order.clear()
            return

        # Invalidate matching entries
        to_remove = []
        for key, entry in self.entries.items():
            if pattern in entry.request_text:
                to_remove.append(key)

        for key in to_remove:
            del self.entries[key]
            if key in self.access_order:
                self.access_order.remove(key)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.stats["total_requests"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0

        # Calculate average access count
        avg_access = 0
        if self.entries:
            avg_access = np.mean([e.access_count for e in self.entries.values()])

        return {
            "entries": len(self.entries),
            "max_entries": self.max_entries,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate_percent": round(hit_rate, 1),
            "evictions": self.stats["evictions"],
            "avg_access_count": round(avg_access, 2),
            "memory_usage_mb": self._estimate_size(),
        }

    def _estimate_size(self) -> float:
        """Estimate memory usage in MB"""
        total = 0
        for entry in self.entries.values():
            total += len(entry.response.encode())
            total += len(entry.request_text.encode())
            if entry.embedding is not None:
                total += entry.embedding.nbytes
        return round(total / 1024 / 1024, 2)

    def get_top_entries(self, n: int = 5) -> List[Dict]:
        """Get most accessed entries"""
        sorted_entries = sorted(
            self.entries.values(), key=lambda e: e.access_count, reverse=True
        )

        results = []
        for entry in sorted_entries[:n]:
            results.append(
                {
                    "request": entry.request_text[:50],
                    "access_count": entry.access_count,
                    "created_at": datetime.fromtimestamp(entry.created_at).isoformat(),
                    "response_preview": entry.response[:50],
                }
            )

        return results


class CacheWithPersistence(SemanticCache):
    """Semantic cache with disk persistence"""

    def __init__(self, *args, cache_file: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_file = cache_file or os.path.expanduser("~/.jarvis_cache.json")
        self._load()

    def save(self):
        """Persist cache to disk"""
        data = {"entries": {}, "stats": self.stats}

        for key, entry in self.entries.items():
            data["entries"][key] = {
                "key": entry.key,
                "request_hash": entry.request_hash,
                "response": entry.response,
                "request_text": entry.request_text,
                "created_at": entry.created_at,
                "last_accessed": entry.last_accessed,
                "access_count": entry.access_count,
                "ttl_seconds": entry.ttl_seconds,
                "embedding": entry.embedding.tolist()
                if entry.embedding is not None
                else None,
                "metadata": entry.metadata,
            }

        try:
            with open(self.cache_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def _load(self):
        """Load cache from disk"""
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, "r") as f:
                data = json.load(f)

            self.stats = data.get("stats", self.stats)

            for key, entry_data in data.get("entries", {}).items():
                embedding = None
                if entry_data.get("embedding"):
                    embedding = np.array(entry_data["embedding"], dtype=np.float32)

                entry = CacheEntry(
                    key=entry_data["key"],
                    request_hash=entry_data["request_hash"],
                    response=entry_data["response"],
                    request_text=entry_data["request_text"],
                    created_at=entry_data["created_at"],
                    last_accessed=entry_data["last_accessed"],
                    access_count=entry_data["access_count"],
                    ttl_seconds=entry_data["ttl_seconds"],
                    embedding=embedding,
                    metadata=entry_data.get("metadata", {}),
                )

                if self._is_valid(entry):
                    self.entries[key] = entry
                    self.access_order.append(key)

            print(f"Loaded {len(self.entries)} cache entries")
        except Exception as e:
            print(f"Warning: Could not load cache: {e}")


class CachedLLMClient:
    """LLM client with semantic caching"""

    def __init__(self, cache: SemanticCache, llm_client=None):
        self.cache = cache
        self.llm_client = llm_client

    async def complete(
        self, prompt: str, system: str = None, use_cache: bool = True
    ) -> str:
        """Complete with caching"""
        if use_cache:
            cached = self.cache.get(prompt)
            if cached:
                print("📦 Cache hit!")
                return cached

        # Generate response (placeholder - would call actual LLM)
        response = f"[Response to: {prompt[:50]}...]"

        if use_cache:
            self.cache.set(prompt, response)

        return response

    def get_stats(self) -> Dict:
        """Get combined stats"""
        return self.cache.get_stats()


def demo():
    """Demo the semantic cache"""
    print("=" * 50)
    print("JARVIS Semantic Cache Demo")
    print("=" * 50)

    cache = SemanticCache(similarity_threshold=0.8, max_entries=100)

    # Test 1: Exact match
    print("\n1. Testing exact match...")
    cache.set("What is the weather?", "The weather is sunny.")
    result = cache.get("What is the weather?")
    print(f"   Result: {result}")

    # Test 2: Similar request (should hit cache)
    print("\n2. Testing semantic similarity...")
    cache.set("Tell me about Python", "Python is a programming language.")
    result = cache.get("What is Python?")
    print(f"   Similar result: {result}")

    # Test 3: Different request (should miss)
    print("\n3. Testing cache miss...")
    result = cache.get("Tell me about JavaScript")
    print(f"   Miss result: {result}")

    # Test 4: Stats
    print("\n4. Cache statistics:")
    stats = cache.get_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")

    # Test 5: Top entries
    print("\n5. Top accessed entries:")
    for entry in cache.get_top_entries():
        print(f"   - {entry['request']}: {entry['access_count']} accesses")


if __name__ == "__main__":
    demo()
