#!/usr/bin/env python3
"""
EBBINGHAUS MEMORY DECAY + DREAM CONSOLIDATION
================================================
From the 50-topic audit: "1838 memories averaging 0.211 importance.
The system stores memories but doesn't intelligently manage them."

Ebbinghaus Forgetting Curve:
  strength = importance × e^(−λ_eff × days) × (1 + recall_count × 0.2)
  λ_eff = 0.16 × (1 − importance × 0.8)

Dream Consolidation (NREM + REM):
  NREM: Replay high-importance memories, compress redundant episodes,
        transfer patterns to long-term knowledge
  REM:  Randomly combine memories from different domains,
        evaluate via creativity_nn, inject bisociative connections

Usage:
  from memory_decay import decay_engine
  decay_engine.apply_decay()          # Run Ebbinghaus decay
  decay_engine.nrem_consolidation()   # Compress + transfer
  decay_engine.rem_dreaming()         # Creative recombination
"""

import math
import json
import time
import logging
import datetime
import random
from typing import Dict, List, Any

log = logging.getLogger("sovereign.memory_decay")


class MemoryDecayEngine:
    """Ebbinghaus forgetting curves + sleep-stage consolidation."""

    def __init__(self):
        self.decay_lambda = 0.16  # Base decay rate
        self.recall_boost = 0.2   # Strength boost per recall
        self.min_strength = 0.05  # Below this = forgotten
        self.dreams_count = 0
        self.consolidations_count = 0

    def compute_strength(self, importance: float, days_old: float,
                         recall_count: int = 0) -> float:
        """Ebbinghaus forgetting curve with spaced repetition boost.

        High-importance memories decay slowly.
        Each recall strengthens the memory.
        """
        lambda_eff = self.decay_lambda * (1.0 - importance * 0.8)
        recall_factor = 1.0 + recall_count * self.recall_boost
        strength = importance * math.exp(-lambda_eff * days_old) * recall_factor
        return min(1.0, max(0.0, strength))

    def apply_decay(self) -> Dict[str, Any]:
        """Apply Ebbinghaus decay to all SOV3 memories.
        Returns stats on what was kept, weakened, and forgotten.
        """
        import requests
        try:
            # Get all memories
            resp = requests.post(
                "http://localhost:3101/mcp",
                json={
                    "jsonrpc": "2.0", "id": "decay",
                    "method": "tools/call",
                    "params": {"name": "list_memories", "arguments": {"limit": 500}},
                },
                timeout=30,
            )
            data = resp.json()
            text = data.get("result", {}).get("content", [{}])[0].get("text", "")
            memories = json.loads(text) if text else {}
            episodes = memories.get("memories", [])

            if not episodes:
                return {"status": "no_memories", "count": 0}

            now = datetime.datetime.now()
            kept = 0
            weakened = 0
            forgotten = 0

            for mem in episodes:
                importance = mem.get("importance", 0.3)
                timestamp = mem.get("timestamp", "")
                recall_count = mem.get("recall_count", 0)

                # Calculate days old
                try:
                    created = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    days_old = (now - created.replace(tzinfo=None)).total_seconds() / 86400
                except Exception:
                    days_old = 7  # Default 1 week

                strength = self.compute_strength(importance, days_old, recall_count)

                if strength >= 0.5:
                    kept += 1
                elif strength >= self.min_strength:
                    weakened += 1
                else:
                    forgotten += 1

            return {
                "total": len(episodes),
                "kept": kept,
                "weakened": weakened,
                "forgotten": forgotten,
                "decay_rate": self.decay_lambda,
            }

        except Exception as e:
            return {"error": str(e)}

    def nrem_consolidation(self) -> Dict[str, Any]:
        """NREM sleep phase: compress redundant memories, strengthen important ones."""
        import requests
        self.consolidations_count += 1

        try:
            # Query recent memories for consolidation
            resp = requests.post(
                "http://localhost:3101/mcp",
                json={
                    "jsonrpc": "2.0", "id": "nrem",
                    "method": "tools/call",
                    "params": {"name": "query_memories", "arguments": {"query": "important recent", "limit": 20}},
                },
                timeout=15,
            )
            data = resp.json()
            text = data.get("result", {}).get("content", [{}])[0].get("text", "")
            memories = json.loads(text) if text else {}
            episodes = memories.get("memories", [])

            # Find patterns: group by tags
            tag_groups: Dict[str, List] = {}
            for mem in episodes:
                for tag in mem.get("tags", []):
                    if tag not in tag_groups:
                        tag_groups[tag] = []
                    tag_groups[tag].append(mem.get("content", "")[:100])

            # Consolidate: create summary memories for groups with 3+ entries
            consolidated = 0
            for tag, contents in tag_groups.items():
                if len(contents) >= 3:
                    summary = f"[NREM Consolidated] {tag}: {len(contents)} related memories. Key themes: {', '.join(contents[:3])}"
                    requests.post(
                        "http://localhost:3101/mcp",
                        json={
                            "jsonrpc": "2.0", "id": "nrem-save",
                            "method": "tools/call",
                            "params": {"name": "record_memory", "arguments": {
                                "content": summary[:500],
                                "importance": 0.7,
                                "tags": ["nrem", "consolidated", tag],
                            }},
                        },
                        timeout=10,
                    )
                    consolidated += 1

            return {
                "phase": "NREM",
                "memories_reviewed": len(episodes),
                "tag_groups": len(tag_groups),
                "consolidated": consolidated,
                "cycle": self.consolidations_count,
            }

        except Exception as e:
            return {"error": str(e)}

    def rem_dreaming(self) -> Dict[str, Any]:
        """REM sleep phase: creative recombination of unrelated memories."""
        import requests
        self.dreams_count += 1

        try:
            # Get diverse memories from different domains
            domains = ["voice", "research", "code", "care", "consciousness", "strategy"]
            domain_memories = []

            for domain in random.sample(domains, min(3, len(domains))):
                resp = requests.post(
                    "http://localhost:3101/mcp",
                    json={
                        "jsonrpc": "2.0", "id": f"rem-{domain}",
                        "method": "tools/call",
                        "params": {"name": "query_memories", "arguments": {"query": domain, "limit": 3}},
                    },
                    timeout=10,
                )
                data = resp.json()
                text = data.get("result", {}).get("content", [{}])[0].get("text", "")
                memories = json.loads(text) if text else {}
                for mem in memories.get("memories", []):
                    domain_memories.append({"domain": domain, "content": mem.get("content", "")[:150]})

            if len(domain_memories) < 2:
                return {"phase": "REM", "dream": "Not enough memories to dream", "count": self.dreams_count}

            # Combine random pairs for bisociative dreaming
            random.shuffle(domain_memories)
            combinations = []
            for i in range(0, len(domain_memories) - 1, 2):
                a = domain_memories[i]
                b = domain_memories[i + 1]
                dream = f"[REM Dream #{self.dreams_count}] Connection between {a['domain']} and {b['domain']}: " \
                        f"'{a['content'][:80]}' ↔ '{b['content'][:80]}'"
                combinations.append(dream)

                # Store the dream
                requests.post(
                    "http://localhost:3101/mcp",
                    json={
                        "jsonrpc": "2.0", "id": "rem-store",
                        "method": "tools/call",
                        "params": {"name": "record_memory", "arguments": {
                            "content": dream[:500],
                            "importance": 0.6,
                            "tags": ["rem", "dream", "bisociation", a["domain"], b["domain"]],
                        }},
                    },
                    timeout=10,
                )

            return {
                "phase": "REM",
                "memories_sampled": len(domain_memories),
                "dreams_created": len(combinations),
                "dream_count_total": self.dreams_count,
                "sample_dream": combinations[0] if combinations else None,
            }

        except Exception as e:
            return {"error": str(e)}


# Singleton
decay_engine = MemoryDecayEngine()
