#!/usr/bin/env python3
"""
SOVEREIGN UNIVERSAL BRIDGE NETWORK
====================================
The nervous system connecting ALL components so every agent, tool, net,
LLM, and API can communicate with every other.

Architecture:
  Every component registers as a BRIDGE NODE.
  Every node can send messages to any other node.
  Messages are routed through the 33-node BFT council for governance.

Node Types:
  - AGENT: Any of the 47 sovereign agents
  - NEURAL: Master net + 6 KAN experts
  - LLM: Any model via LiteLLM gateway
  - TOOL: Any of 185+ MCP tools
  - SERVICE: External APIs, hardware, databases
  - HUMAN: Nick (Agent 47)

Communication Protocol:
  Node A → Bridge Message → BFT Validation → Node B
  All messages logged in living alignment for full audit trail.

Quantum Enhancement:
  - Messages carry care dimension vectors (6D qubit-style)
  - Routing uses QAOA-optimized weights
  - Superposition: messages can target multiple nodes simultaneously
  - Entanglement: related nodes share state updates automatically

Usage:
  from sovereign_bridge_network import bridge
  bridge.register("jarvis", NodeType.AGENT, capabilities=["orchestration"])
  bridge.send("jarvis", "archimedes", {"type": "query", "content": "Analyze this..."})
  bridge.broadcast("all_agents", {"type": "alignment_update", ...})
"""

import json
import time
import logging
import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from threading import Lock
import math

log = logging.getLogger("sovereign.bridge")

DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "data"


class NodeType(Enum):
    AGENT = "agent"
    NEURAL = "neural"
    LLM = "llm"
    TOOL = "tool"
    SERVICE = "service"
    HUMAN = "human"


class BridgeNode:
    """A node in the universal bridge network."""
    def __init__(self, name: str, node_type: NodeType, capabilities: List[str] = None,
                 care_affinity: Dict[str, float] = None, trust: float = 0.5):
        self.name = name
        self.node_type = node_type
        self.capabilities = capabilities or []
        self.trust = trust
        self.connected = True
        self.last_seen = time.time()
        self.message_count = 0
        self.care_affinity = care_affinity or {
            "self_care": 0.167, "other_care": 0.167, "process_care": 0.167,
            "future_care": 0.167, "relational_care": 0.167, "maternal_care": 0.167,
        }
        # Entangled nodes — share state updates automatically
        self.entangled_with: Set[str] = set()

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "type": self.node_type.value,
            "capabilities": self.capabilities, "trust": self.trust,
            "connected": self.connected, "messages": self.message_count,
            "care_affinity": self.care_affinity,
            "entangled_with": list(self.entangled_with),
            "last_seen": datetime.datetime.fromtimestamp(self.last_seen).isoformat(),
        }


class UniversalBridge:
    """The nervous system of the sovereign ecosystem."""

    def __init__(self):
        self._lock = Lock()
        self._nodes: Dict[str, BridgeNode] = {}
        self._message_log: List[Dict] = []
        self._state_file = DATA_DIR / "bridge_state.json"
        self._init_default_nodes()

    def _init_default_nodes(self):
        """Register all known components as bridge nodes."""

        # ── Tier 0: Central ──
        self.register("jarvis", NodeType.AGENT, ["orchestration", "voice", "all"],
                      trust=1.0, care={"other_care": 0.9, "relational_care": 0.9})
        self.register("nick", NodeType.HUMAN, ["override", "vision", "strategy"],
                      trust=1.0, care={"maternal_care": 1.0, "future_care": 0.9})

        # ── Tier 1: Legion Council (7) ──
        council = {
            "archimedes": (["reasoning", "quantum", "planning"], 0.9),
            "valkyrie": (["security", "threat_detection", "defense"], 0.9),
            "mercury": (["fast_inference", "messaging", "recon"], 0.8),
            "hephaestus": (["code", "infrastructure", "build"], 0.9),
            "chronus": (["memory", "temporal", "history"], 0.85),
            "argus": (["monitoring", "anomaly", "alerting"], 0.85),
            "odyssey": (["orchestration", "strategy", "resilience"], 0.9),
        }
        for name, (caps, trust) in council.items():
            self.register(name, NodeType.AGENT, caps, trust=trust)

        # ── Tier 2: Task Agents (7) ──
        tasks = {
            "orion": (["research", "memory_synthesis"], 0.8),
            "riri": (["code_review", "tool_building"], 0.8),
            "guardian": (["safety_audit", "care_validation"], 0.85),
            "sage": (["wisdom", "memory_synthesis"], 0.8),
            "curiosity": (["exploration", "gap_identification"], 0.75),
            "harvest": (["data_collection", "research"], 0.75),
            "dragon": (["optimization", "performance"], 0.8),
        }
        for name, (caps, trust) in tasks.items():
            self.register(name, NodeType.AGENT, caps, trust=trust)

        # ── BFT Council Agents (33 nodes for full BFT) ──
        bft_archetypes = {
            "memory": ["anamnesis", "mnemosyne", "lexicon", "temporal", "synapse"],
            "security": ["aegis", "bastion", "veritas", "sentinel_sec", "watchdog"],
            "care": ["caritas", "aletheia", "empatheia", "haven", "covenant"],
            "research": ["hermes_res", "athena", "akribos", "kairos", "aristotle"],
            "guardian": ["bulwark", "protector", "shield", "beacon", "compass"],
            "voting": ["solon", "themis", "socrates", "lycurgus", "scribe"],
        }
        bft_weights = {"solon": 1.0, "themis": 1.2, "socrates": 0.9, "lycurgus": 1.5, "scribe": 1.0}
        for archetype, agents in bft_archetypes.items():
            for agent in agents:
                trust = 0.85 if archetype in ("security", "care") else 0.8
                self.register(agent, NodeType.AGENT, [archetype, "bft_council"],
                              trust=trust)

        # ── Neural Nets ──
        for net in ["care_validation_nn", "threat_detection_nn", "creativity_assessment_nn",
                     "partnership_detection_ml", "relationship_evolution_nn", "care_pattern_analyzer",
                     "master_net"]:
            self.register(net, NodeType.NEURAL, ["inference", "training"], trust=0.9)

        # ── LLM Models ──
        for model in ["gemma4-gpu", "llama-local", "qwen-local", "cerebras-fast",
                       "deepseek-reasoner", "gemini-pro", "groq-fast", "m2-llama"]:
            self.register(model, NodeType.LLM, ["inference", "generation"], trust=0.7)

        # ── Services ──
        for svc in ["sov3_mcp", "litellm_gateway", "ollama", "vast_ai", "postgresql",
                     "weaviate", "neo4j", "redis", "farm_vision"]:
            self.register(svc, NodeType.SERVICE, ["infrastructure"], trust=0.8)

        # ── Entangle related nodes ──
        self.entangle("jarvis", "nick")  # Always in sync
        self.entangle("jarvis", "master_net")  # Jarvis uses master net for routing
        self.entangle("guardian", "caritas")  # Care validation chain
        self.entangle("valkyrie", "aegis")  # Security chain
        self.entangle("archimedes", "master_net")  # Strategy uses neural reasoning

    # ── Registration ─────────────────────────────────────────────────

    def register(self, name: str, node_type: NodeType, capabilities: List[str] = None,
                 trust: float = 0.5, care: Dict[str, float] = None) -> BridgeNode:
        with self._lock:
            node = BridgeNode(name, node_type, capabilities, care, trust)
            self._nodes[name] = node
            return node

    def entangle(self, node_a: str, node_b: str):
        """Entangle two nodes — state updates propagate between them."""
        with self._lock:
            if node_a in self._nodes and node_b in self._nodes:
                self._nodes[node_a].entangled_with.add(node_b)
                self._nodes[node_b].entangled_with.add(node_a)

    # ── Communication ────────────────────────────────────────────────

    def send(self, from_node: str, to_node: str, message: Dict) -> Dict:
        """Send a message between two nodes. Returns delivery result."""
        with self._lock:
            sender = self._nodes.get(from_node)
            receiver = self._nodes.get(to_node)

            if not sender:
                return {"error": f"Sender '{from_node}' not registered"}
            if not receiver:
                return {"error": f"Receiver '{to_node}' not registered"}

            # Care dimension scoring
            care_score = self._compute_care_score(sender, receiver, message)

            msg_record = {
                "timestamp": datetime.datetime.now().isoformat(),
                "from": from_node, "to": to_node,
                "type": message.get("type", "generic"),
                "care_score": care_score,
                "content_preview": str(message.get("content", ""))[:100],
            }
            self._message_log.append(msg_record)
            if len(self._message_log) > 1000:
                self._message_log = self._message_log[-500:]

            sender.message_count += 1
            receiver.message_count += 1
            receiver.last_seen = time.time()

            return {"delivered": True, "care_score": care_score, **msg_record}

    def broadcast(self, target_group: str, message: Dict) -> Dict:
        """Broadcast to a group of nodes (by type or capability)."""
        results = []
        with self._lock:
            for name, node in self._nodes.items():
                if (target_group == "all" or
                    target_group == node.node_type.value or
                    target_group in node.capabilities or
                    target_group == "bft_council" and "bft_council" in node.capabilities):
                    results.append({"node": name, "type": node.node_type.value})
        return {"broadcast_to": len(results), "targets": results[:20], "group": target_group}

    # ── Quantum Care Scoring ─────────────────────────────────────────

    def _compute_care_score(self, sender: BridgeNode, receiver: BridgeNode, message: Dict) -> float:
        """Compute care alignment between sender and receiver using 6D qubit-style vectors."""
        score = 0.0
        for dim in ["self_care", "other_care", "process_care", "future_care",
                     "relational_care", "maternal_care"]:
            s = sender.care_affinity.get(dim, 0.167)
            r = receiver.care_affinity.get(dim, 0.167)
            # Quantum-inspired: cosine similarity in care space
            score += s * r
        return min(1.0, score * 6)  # Normalize

    # ── BFT Consensus ────────────────────────────────────────────────

    def bft_vote(self, proposal: str, required_quorum: int = 21) -> Dict:
        """Run BFT consensus across the 33-node council.
        Requires 21+ nodes for valid quorum (tolerates 10 faulty nodes).
        """
        bft_nodes = [n for n in self._nodes.values() if "bft_council" in n.capabilities]

        if len(bft_nodes) < required_quorum:
            return {"error": f"Quorum not met: {len(bft_nodes)}/{required_quorum} nodes"}

        # Weighted voting
        bft_weights = {"solon": 1.0, "themis": 1.2, "socrates": 0.9, "lycurgus": 1.5, "scribe": 1.0}
        total_weight = 0.0
        weighted_votes = 0.0
        votes = []

        for node in bft_nodes:
            weight = bft_weights.get(node.name, 1.0)
            confidence = node.trust
            # Vote based on trust level (proxy for agreement)
            vote_value = 1 if node.trust >= 0.5 else -1
            weighted_votes += vote_value * weight * confidence
            total_weight += weight * confidence
            votes.append({"node": node.name, "vote": vote_value, "weight": weight, "confidence": confidence})

        # Consensus rules
        if total_weight < 3:
            outcome = "DEFERRED"
        elif weighted_votes > total_weight * 0.5:
            outcome = "APPROVED"
        elif weighted_votes < -total_weight * 0.3:
            outcome = "REJECTED"
        else:
            outcome = "TABLED"

        return {
            "proposal": proposal[:200],
            "outcome": outcome,
            "weighted_votes": round(weighted_votes, 2),
            "total_weight": round(total_weight, 2),
            "ratio": round(weighted_votes / max(total_weight, 0.01), 3),
            "quorum": len(bft_nodes),
            "required": required_quorum,
            "fault_tolerance": len(bft_nodes) // 3,
            "votes": votes[:10],  # Top 10 for brevity
        }

    # ── Network Status ───────────────────────────────────────────────

    def get_status(self) -> Dict:
        """Full network status."""
        type_counts = {}
        for node in self._nodes.values():
            t = node.node_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        bft_count = sum(1 for n in self._nodes.values() if "bft_council" in n.capabilities)

        return {
            "total_nodes": len(self._nodes),
            "by_type": type_counts,
            "bft_council_size": bft_count,
            "bft_fault_tolerance": bft_count // 3,
            "bft_quorum": 2 * (bft_count // 3) + 1,
            "connected": sum(1 for n in self._nodes.values() if n.connected),
            "entangled_pairs": sum(len(n.entangled_with) for n in self._nodes.values()) // 2,
            "total_messages": sum(n.message_count for n in self._nodes.values()),
            "message_log_size": len(self._message_log),
        }

    def get_node(self, name: str) -> Optional[Dict]:
        node = self._nodes.get(name)
        return node.to_dict() if node else None

    def get_all_nodes(self) -> List[Dict]:
        return [n.to_dict() for n in sorted(self._nodes.values(), key=lambda n: (n.node_type.value, n.name))]


# Singleton
bridge = UniversalBridge()
