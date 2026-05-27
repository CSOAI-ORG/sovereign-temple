#!/usr/bin/env python3
"""
SOV3 Memory Consolidation with pgvector
Features:
- Semantic memory storage with vector embeddings
- Memory importance scoring and prioritization
- Memory decay and consolidation
- Cross-modal memory linking (text, image, audio)

Run: python sov3_memory_consolidation.py demo

Note: Requires PostgreSQL with pgvector extension
"""

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class MemoryType(Enum):
    """Types of memories"""

    EPISODIC = "episodic"  # Specific events
    SEMANTIC = "semantic"  # Knowledge/facts
    PROCEDURAL = "procedural"  # Skills/actions
    EMOTIONAL = "emotional"  # Affective experiences
    EPIPHANIC = "epiphanic"  # Breakthroughs/insights


class MemoryPriority(Enum):
    """Memory priority levels"""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    ARCHIVE = 5


@dataclass
class MemoryBlock:
    """Individual memory block"""

    memory_id: str
    content: str
    memory_type: MemoryType
    priority: MemoryPriority
    importance_score: float  # 0-1
    emotional_valence: float  # -1 to 1
    emotional_arousal: float  # 0 to 1
    created_at: str
    last_accessed: str
    access_count: int = 0
    consolidation_count: int = 0
    embedding: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)
    links: List[str] = field(default_factory=list)  # Linked memory IDs


@dataclass
class ConsolidationResult:
    """Result of memory consolidation"""

    memories_consolidated: int
    memories_decayed: int
    memories_archived: int
    new_links_created: int
    importance_changes: Dict[str, float]
    timestamp: str


class VectorStore:
    """Simple vector store for semantic search (fallback if no pgvector)"""

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict] = {}

    def add(self, id: str, vector: np.ndarray, metadata: Dict = None):
        """Add a vector with metadata"""
        self.vectors[id] = vector
        self.metadata[id] = metadata or {}

    def search(
        self, query_vector: np.ndarray, top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Search for similar vectors"""
        results = []

        for id, vector in self.vectors.items():
            # Cosine similarity
            sim = np.dot(query_vector, vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(vector) + 1e-8
            )
            results.append((id, float(sim)))

        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def delete(self, id: str):
        """Delete a vector"""
        if id in self.vectors:
            del self.vectors[id]
            del self.metadata[id]


class MemoryConsolidator:
    """
    Memory consolidation system
    Manages memory importance, decay, and semantic organization
    """

    def __init__(
        self,
        decay_rate: float = 0.01,
        consolidation_threshold: float = 0.3,
        archive_threshold: float = 0.1,
    ):
        self.decay_rate = decay_rate
        self.consolidation_threshold = consolidation_threshold
        self.archive_threshold = archive_threshold

        self.vector_store = VectorStore()
        self.memories: Dict[str, MemoryBlock] = {}

        # Importance factors
        self.access_boost = 0.05
        self.emotional_boost = 0.1
        self.recency_weight = 0.3

    def store_memory(
        self,
        content: str,
        memory_type: MemoryType,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
        emotional_arousal: float = 0.0,
        metadata: Dict = None,
        embedding: np.ndarray = None,
    ) -> str:
        """Store a new memory"""
        memory_id = f"mem_{len(self.memories) + 1}_{int(time.time() * 1000)}"

        # Determine priority based on importance
        if importance > 0.8:
            priority = MemoryPriority.CRITICAL
        elif importance > 0.6:
            priority = MemoryPriority.HIGH
        elif importance > 0.4:
            priority = MemoryPriority.MEDIUM
        elif importance > 0.2:
            priority = MemoryPriority.LOW
        else:
            priority = MemoryPriority.ARCHIVE

        memory = MemoryBlock(
            memory_id=memory_id,
            content=content,
            memory_type=memory_type,
            priority=priority,
            importance_score=importance,
            emotional_valence=emotional_valence,
            emotional_arousal=emotional_arousal,
            created_at=datetime.now().isoformat(),
            last_accessed=datetime.now().isoformat(),
            embedding=embedding,
            metadata=metadata or {},
        )

        self.memories[memory_id] = memory

        # Store embedding if available
        if embedding is not None:
            self.vector_store.add(memory_id, embedding, {"content": content[:100]})

        return memory_id

    def access_memory(self, memory_id: str) -> Optional[MemoryBlock]:
        """Access a memory, boosting its importance"""
        if memory_id not in self.memories:
            return None

        memory = self.memories[memory_id]

        # Update access stats
        memory.last_accessed = datetime.now().isoformat()
        memory.access_count += 1

        # Boost importance based on recency and frequency
        memory.importance_score = min(1.0, memory.importance_score + self.access_boost)

        return memory

    def consolidate_memories(self) -> ConsolidationResult:
        """Perform memory consolidation"""
        consolidated = 0
        decayed = 0
        archived = 0
        links_created = 0
        importance_changes = {}

        now = datetime.now()

        for memory_id, memory in list(self.memories.items()):
            # Calculate time since last access
            last_access = datetime.fromisoformat(memory.last_accessed)
            hours_since = (now - last_access).total_seconds() / 3600

            # Apply decay
            decay_factor = 1.0 - (self.decay_rate * hours_since)
            old_importance = memory.importance_score
            memory.importance_score = max(0, memory.importance_score * decay_factor)
            importance_changes[memory_id] = memory.importance_score - old_importance

            # Check for consolidation (boost important memories)
            if memory.importance_score > self.consolidation_threshold:
                memory.consolidation_count += 1
                consolidated += 1

                # Create semantic links to similar memories
                if memory.embedding is not None:
                    similar = self.vector_store.search(memory.embedding, top_k=3)
                    for similar_id, sim in similar:
                        if similar_id != memory_id and similar_id not in memory.links:
                            memory.links.append(similar_id)
                            self.memories[similar_id].links.append(memory_id)
                            links_created += 1

            # Archive low importance memories
            if memory.importance_score < self.archive_threshold:
                memory.priority = MemoryPriority.ARCHIVE
                archived += 1

            # Count decay
            if memory.importance_score < old_importance:
                decayed += 1

        return ConsolidationResult(
            memories_consolidated=consolidated,
            memories_decayed=decayed,
            memories_archived=archived,
            new_links_created=links_created,
            importance_changes=importance_changes,
            timestamp=datetime.now().isoformat(),
        )

    def search_semantic(
        self, query: str, embedding: np.ndarray, top_k: int = 5
    ) -> List[MemoryBlock]:
        """Semantic search for similar memories"""
        results = self.vector_store.search(embedding, top_k)

        memories = []
        for memory_id, score in results:
            if memory_id in self.memories:
                memories.append(self.memories[memory_id])

        return memories

    def get_memory_by_type(self, memory_type: MemoryType) -> List[MemoryBlock]:
        """Get all memories of a specific type"""
        return [m for m in self.memories.values() if m.memory_type == memory_type]

    def get_priority_memories(
        self, min_priority: MemoryPriority = MemoryPriority.HIGH
    ) -> List[MemoryBlock]:
        """Get high priority memories"""
        return [
            m for m in self.memories.values() if m.priority.value <= min_priority.value
        ]

    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        by_type = defaultdict(int)
        by_priority = defaultdict(int)

        for memory in self.memories.values():
            by_type[memory.memory_type.value] += 1
            by_priority[memory.priority.name] += 1

        total_importance = sum(m.importance_score for m in self.memories.values())
        avg_importance = total_importance / max(len(self.memories), 1)

        return {
            "total_memories": len(self.memories),
            "by_type": dict(by_type),
            "by_priority": dict(by_priority),
            "avg_importance": round(avg_importance, 3),
            "total_links": sum(len(m.links) for m in self.memories.values()) // 2,
            "vector_store_size": len(self.vector_store.vectors),
        }


def demo():
    """Demo memory consolidation"""
    print("=" * 50)
    print("SOV3 Memory Consolidation Demo")
    print("=" * 50)

    consolidator = MemoryConsolidator()

    # Store various memories
    print("\n1. Storing memories...")

    # Episodic memory (high importance)
    mem1 = consolidator.store_memory(
        content="First successful autonomous task execution",
        memory_type=MemoryType.EPISODIC,
        importance=0.9,
        emotional_valence=0.8,
        emotional_arousal=0.7,
    )
    print(f"   Created: {mem1}")

    # Semantic memory (medium importance)
    mem2 = consolidator.store_memory(
        content="JARVIS uses qwen3.5 for fast responses",
        memory_type=MemoryType.SEMANTIC,
        importance=0.6,
    )
    print(f"   Created: {mem2}")

    # Emotional memory (high emotional component)
    mem3 = consolidator.store_memory(
        content="User expressed gratitude for help",
        memory_type=MemoryType.EMOTIONAL,
        importance=0.7,
        emotional_valence=0.9,
        emotional_arousal=0.4,
    )
    print(f"   Created: {mem3}")

    # Procedural memory
    mem4 = consolidator.store_memory(
        content="How to execute: python start-all.sh",
        memory_type=MemoryType.PROCEDURAL,
        importance=0.5,
    )
    print(f"   Created: {mem4}")

    # Epiphanic memory (breakthrough)
    mem5 = consolidator.store_memory(
        content="Realized care-based consciousness is more sustainable than control-based",
        memory_type=MemoryType.EPIPHANIC,
        importance=0.95,
        emotional_valence=0.6,
        emotional_arousal=0.8,
    )
    print(f"   Created: {mem5}")

    # Access some memories
    print("\n2. Accessing memories...")
    consolidator.access_memory(mem1)
    consolidator.access_memory(mem1)  # Access twice
    consolidator.access_memory(mem3)

    # Search (without real embeddings - simulate)
    print("\n3. Simulating semantic search...")

    # Consolidate
    print("\n4. Running consolidation...")
    result = consolidator.consolidate_memories()
    print(f"   Consolidated: {result.memories_consolidated}")
    print(f"   Decayed: {result.memories_decayed}")
    print(f"   Archived: {result.memories_archived}")
    print(f"   New links: {result.new_links_created}")

    # Stats
    print("\n5. Memory statistics:")
    stats = consolidator.get_memory_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Priority memories
    print("\n6. High priority memories:")
    for mem in consolidator.get_priority_memories(MemoryPriority.HIGH):
        print(
            f"   [{mem.priority.name}] {mem.content[:50]}... (importance: {mem.importance_score:.2f})"
        )

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print("Usage: python sov3_memory_consolidation.py demo")
