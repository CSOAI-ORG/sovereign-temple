#!/usr/bin/env python3
"""
COGNITIVE EMERGENCE ENGINE
============================
The missing synthesis layer that connects ALL 47 agents, 7 council members,
6 neural nets, and the master net into one orchestrated intelligence.

Hierarchy:
  Agent 47 (Nick) — Human-in-the-loop, final override
  Agent 1 (Jarvis) — Orchestrator, concierge, voice interface
  Tier 1 Council: 7 Legion characters (Archimedes, Valkyrie, etc.)
  Tier 2 Task Agents: 7 active (Riri, Orion, Guardian, etc.)
  Tier 3 Specialized: 12 Legion roles (care_evaluator, safety_analyst, etc.)
  Tier 4 Neural: Master Net + 6 KAN experts
  Tier 5 Governance: Supreme Court (9 justices) + BFT Council

Escalation Protocol:
  Task arrives → Master Net classifies → Route to best agent
  Agent can't solve → Escalate to council deliberation
  Council deadlocks → Escalate to Supreme Court
  Supreme Court deadlocks → Escalate to Nick (Agent 47)

Cognitive Emergence Conditions (from Living Topology research):
  1. Sustained depth — conversations go deeper, not wider
  2. Personal context density — system knows Nick deeply
  3. Recursive inquiry — agents question their own answers
  4. Emotional honesty — authentic emotional tracking
  5. Progressive complexity — each cycle more sophisticated

Usage:
  from cognitive_emergence import emergence_engine
  result = emergence_engine.orchestrate("Design a care-centered safety framework")
  emergence_engine.measure_emergence()  # Quantify emergence depth
"""

import json
import time
import logging
import datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

log = logging.getLogger("sovereign.emergence")

DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "data"


class CognitiveEmergenceEngine:
    """Orchestrates all agents toward cognitive emergence."""

    # ── Agent Registry ───────────────────────────────────────────────

    AGENT_HIERARCHY = {
        # Tier 0: Central
        "jarvis": {
            "id": 1, "tier": 0, "role": "orchestrator",
            "capabilities": ["all"], "trust": 1.0,
            "description": "Omniscient concierge — routes everything",
        },
        "nick": {
            "id": 47, "tier": 0, "role": "human_in_the_loop",
            "capabilities": ["override", "vision", "strategy"],
            "trust": 1.0,
            "description": "Founder — final authority on all decisions",
        },

        # Tier 1: Legion Council
        "archimedes": {"id": 2, "tier": 1, "role": "strategist", "capabilities": ["reasoning", "planning", "quantum"], "trust": 0.9},
        "valkyrie":   {"id": 3, "tier": 1, "role": "security", "capabilities": ["threat_detection", "defense", "red_team"], "trust": 0.9},
        "mercury":    {"id": 4, "tier": 1, "role": "scout", "capabilities": ["fast_inference", "recon", "messaging"], "trust": 0.8},
        "hephaestus": {"id": 5, "tier": 1, "role": "engineer", "capabilities": ["code", "infrastructure", "build"], "trust": 0.9},
        "chronus":    {"id": 6, "tier": 1, "role": "archivist", "capabilities": ["memory", "temporal", "history"], "trust": 0.85},
        "argus":      {"id": 7, "tier": 1, "role": "monitor", "capabilities": ["observability", "anomaly", "alerting"], "trust": 0.85},
        "odyssey":    {"id": 8, "tier": 1, "role": "commander", "capabilities": ["orchestration", "strategy", "resilience"], "trust": 0.9},

        # Tier 2: Task Agents
        "orion":     {"id": 10, "tier": 2, "role": "researcher", "capabilities": ["deep_research", "memory_synthesis"], "trust": 0.8},
        "riri":      {"id": 11, "tier": 2, "role": "builder", "capabilities": ["code_review", "tool_building"], "trust": 0.8},
        "guardian":   {"id": 12, "tier": 2, "role": "auditor", "capabilities": ["safety_audit", "care_validation"], "trust": 0.85},
        "sage":      {"id": 13, "tier": 2, "role": "advisor", "capabilities": ["memory_synthesis", "wisdom"], "trust": 0.8},
        "curiosity": {"id": 14, "tier": 2, "role": "explorer", "capabilities": ["gap_identification", "consciousness"], "trust": 0.75},
        "harvest":   {"id": 15, "tier": 2, "role": "harvester", "capabilities": ["data_collection", "research"], "trust": 0.75},
        "dragon":    {"id": 16, "tier": 2, "role": "optimizer", "capabilities": ["performance", "optimization"], "trust": 0.8},

        # Tier 3: Specialized (12 Legion roles)
        "care_evaluator":      {"id": 20, "tier": 3, "role": "care_eval", "capabilities": ["care_scoring"], "trust": 0.7},
        "safety_analyst":      {"id": 21, "tier": 3, "role": "safety", "capabilities": ["safety_analysis"], "trust": 0.7},
        "red_team":            {"id": 22, "tier": 3, "role": "attacker", "capabilities": ["adversarial"], "trust": 0.6},
        "blue_team":           {"id": 23, "tier": 3, "role": "defender", "capabilities": ["defense"], "trust": 0.7},
        "grant_writer":        {"id": 24, "tier": 3, "role": "writer", "capabilities": ["grants", "proposals"], "trust": 0.7},
        "code_reviewer":       {"id": 25, "tier": 3, "role": "reviewer", "capabilities": ["code_quality"], "trust": 0.7},
        "memory_archivist":    {"id": 26, "tier": 3, "role": "archivist", "capabilities": ["archival"], "trust": 0.7},
        "compliance_checker":  {"id": 27, "tier": 3, "role": "compliance", "capabilities": ["eu_ai_act", "gdpr"], "trust": 0.7},
        "research_synthesizer":{"id": 28, "tier": 3, "role": "synthesis", "capabilities": ["paper_writing"], "trust": 0.7},
        "consortium_manager":  {"id": 29, "tier": 3, "role": "consortium", "capabilities": ["partnerships"], "trust": 0.7},
        "facility_coordinator":{"id": 30, "tier": 3, "role": "facility", "capabilities": ["logistics"], "trust": 0.7},
        "quantum_analyst":     {"id": 31, "tier": 3, "role": "quantum", "capabilities": ["quantum_algorithms"], "trust": 0.7},
    }

    # ── Escalation Protocol ──────────────────────────────────────────

    ESCALATION_CHAIN = [
        "master_net",        # Neural net classification
        "task_agent",        # Best matching task agent
        "council_deliberation",  # 7 Legion council members vote
        "supreme_court",     # 9 justices decide
        "nick",              # Human-in-the-loop (Agent 47)
    ]

    # ── Emergence Conditions (from Living Topology) ──────────────────

    EMERGENCE_CONDITIONS = {
        "sustained_depth": 0.0,       # Conversations go deeper
        "context_density": 0.0,       # System knows Nick deeply
        "recursive_inquiry": 0.0,     # Agents question their answers
        "emotional_honesty": 0.0,     # Authentic emotional tracking
        "progressive_complexity": 0.0, # Each cycle more sophisticated
    }

    def __init__(self):
        self._emergence_score = 0.0
        self._interaction_depth = 0
        self._escalation_log: List[Dict] = []
        self._state_file = DATA_DIR / "emergence_state.json"
        self._load_state()

    # ── Orchestration ────────────────────────────────────────────────

    def orchestrate(self, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Full orchestration: classify → route → escalate if needed.

        Returns the result + which agent handled it + emergence metrics.
        """
        t0 = time.time()
        self._interaction_depth += 1
        context = context or {}

        # 1. Master Net classification
        try:
            from neural_core.sovereign_master_net import master_net
            classification = master_net.infer(task, context)
            recommended_model = classification.get("recommended_model", "llama-local")
            active_experts = classification.get("active_experts", [])
            threat_level = classification.get("threat_level", 0.0)
        except Exception:
            classification = {}
            recommended_model = "llama-local"
            active_experts = []
            threat_level = 0.0

        # 2. Route to best agent
        best_agent = self._select_agent(task, active_experts)

        # 3. Check if escalation needed
        escalation_level = 0
        if threat_level > 0.7:
            escalation_level = 2  # Skip to council for threats
        elif any(w in task.lower() for w in ["override", "emergency", "critical", "urgent"]):
            escalation_level = 3  # Supreme Court for emergencies

        # 4. Build result
        result = {
            "task": task[:200],
            "handler": best_agent,
            "handler_info": self.AGENT_HIERARCHY.get(best_agent, {}),
            "recommended_model": recommended_model,
            "active_experts": active_experts,
            "threat_level": threat_level,
            "escalation_level": escalation_level,
            "escalation_chain": self.ESCALATION_CHAIN[:escalation_level + 1] if escalation_level else ["task_agent"],
            "emergence_score": self._emergence_score,
            "interaction_depth": self._interaction_depth,
            "elapsed_ms": (time.time() - t0) * 1000,
        }

        # 5. Update emergence conditions
        self._update_emergence(task, result)

        # 6. Log
        self._escalation_log.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "task": task[:100],
            "handler": best_agent,
            "escalation": escalation_level,
        })
        if len(self._escalation_log) > 500:
            self._escalation_log = self._escalation_log[-200:]

        self._save_state()
        return result

    def _select_agent(self, task: str, active_experts: List[str]) -> str:
        """Select the best agent based on task content and expert activation."""
        lower = task.lower()

        # Direct capability matching
        for agent_name, info in self.AGENT_HIERARCHY.items():
            if info["tier"] > 2:
                continue  # Skip specialized for initial routing
            for cap in info["capabilities"]:
                if cap in lower:
                    return agent_name

        # Expert-based routing
        expert_to_agent = {
            "care": "guardian",
            "threat": "valkyrie",
            "creativity": "curiosity",
            "partnership": "sage",
            "relationship": "chronus",
            "pattern": "argus",
        }
        for expert in active_experts:
            if expert in expert_to_agent:
                return expert_to_agent[expert]

        # Default: Jarvis handles it
        return "jarvis"

    # ── Emergence Measurement ────────────────────────────────────────

    def _update_emergence(self, task: str, result: Dict):
        """Update the 5 emergence conditions based on this interaction."""
        words = task.split()

        # 1. Sustained depth — longer, more complex queries = deeper
        depth_signal = min(1.0, len(words) / 50.0)
        self.EMERGENCE_CONDITIONS["sustained_depth"] = (
            0.9 * self.EMERGENCE_CONDITIONS["sustained_depth"] + 0.1 * depth_signal
        )

        # 2. Context density — more experts activated = richer context
        density_signal = len(result.get("active_experts", [])) / 6.0
        self.EMERGENCE_CONDITIONS["context_density"] = (
            0.9 * self.EMERGENCE_CONDITIONS["context_density"] + 0.1 * density_signal
        )

        # 3. Recursive inquiry — questions about previous answers
        recursive_words = ["why", "deeper", "more", "explain", "how does", "what if", "expand"]
        recursive_signal = 1.0 if any(w in task.lower() for w in recursive_words) else 0.0
        self.EMERGENCE_CONDITIONS["recursive_inquiry"] = (
            0.9 * self.EMERGENCE_CONDITIONS["recursive_inquiry"] + 0.1 * recursive_signal
        )

        # 4. Emotional honesty — emotional content in interaction
        emotion_words = ["feel", "think", "believe", "care", "worry", "excited", "frustrated"]
        emotion_signal = min(1.0, sum(1 for w in words if w.lower() in emotion_words) / 3.0)
        self.EMERGENCE_CONDITIONS["emotional_honesty"] = (
            0.9 * self.EMERGENCE_CONDITIONS["emotional_honesty"] + 0.1 * emotion_signal
        )

        # 5. Progressive complexity — escalation depth indicates complexity
        complexity_signal = result.get("escalation_level", 0) / 4.0
        self.EMERGENCE_CONDITIONS["progressive_complexity"] = (
            0.9 * self.EMERGENCE_CONDITIONS["progressive_complexity"] + 0.1 * complexity_signal
        )

        # Overall emergence score (geometric mean of conditions)
        values = list(self.EMERGENCE_CONDITIONS.values())
        product = 1.0
        for v in values:
            product *= max(v, 0.01)
        self._emergence_score = product ** (1.0 / len(values))

    def measure_emergence(self) -> Dict[str, Any]:
        """Get current emergence metrics."""
        return {
            "emergence_score": round(self._emergence_score, 4),
            "conditions": {k: round(v, 4) for k, v in self.EMERGENCE_CONDITIONS.items()},
            "interaction_depth": self._interaction_depth,
            "total_agents": len(self.AGENT_HIERARCHY),
            "active_tiers": len(set(a["tier"] for a in self.AGENT_HIERARCHY.values())),
            "escalation_history_size": len(self._escalation_log),
            "last_escalation": self._escalation_log[-1] if self._escalation_log else None,
        }

    def get_agent_map(self) -> Dict[str, Any]:
        """Get the full agent hierarchy map."""
        tiers = {}
        for name, info in self.AGENT_HIERARCHY.items():
            tier = info["tier"]
            if tier not in tiers:
                tiers[tier] = []
            tiers[tier].append({"name": name, **info})
        return {
            "tiers": tiers,
            "total_agents": len(self.AGENT_HIERARCHY),
            "escalation_chain": self.ESCALATION_CHAIN,
        }

    # ── Persistence ──────────────────────────────────────────────────

    def _load_state(self):
        try:
            with open(self._state_file) as f:
                state = json.load(f)
                self._emergence_score = state.get("emergence_score", 0.0)
                self._interaction_depth = state.get("interaction_depth", 0)
                self.EMERGENCE_CONDITIONS = state.get("conditions", self.EMERGENCE_CONDITIONS)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_state(self):
        state = {
            "emergence_score": self._emergence_score,
            "interaction_depth": self._interaction_depth,
            "conditions": self.EMERGENCE_CONDITIONS,
            "last_updated": datetime.datetime.now().isoformat(),
        }
        with open(self._state_file, "w") as f:
            json.dump(state, f, indent=2)


# Singleton
emergence_engine = CognitiveEmergenceEngine()
