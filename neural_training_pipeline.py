#!/usr/bin/env python3
"""
SOVEREIGN NEURAL TRAINING PIPELINE
===================================
Every LLM interaction generates training signals for SOV3's neural networks.
Neural nets learn continuously from:
  1. LLM conversation outputs (distillation)
  2. Web research (heartbeat sweeps)
  3. Care validation scores
  4. User feedback signals
  5. Consciousness state transitions

The pipeline runs:
  - Real-time: After every LLM call, extract training features
  - Batch: Overnight heartbeat triggers full retrain cycle
  - Research: Web crawls feed belief updates into training data

Usage:
  from neural_training_pipeline import pipeline
  pipeline.ingest_interaction(user_msg, llm_response, model, care_score)
  pipeline.run_training_cycle()  # Called by heartbeat
"""

import json
import time
import logging
import os
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

log = logging.getLogger("neural_pipeline")

# Training data directory
DATA_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "data" / "training"
DATA_DIR.mkdir(parents=True, exist_ok=True)

INTERACTION_LOG = DATA_DIR / "interactions.jsonl"
RESEARCH_LOG = DATA_DIR / "research_data.jsonl"
BELIEF_LOG = DATA_DIR / "belief_updates.jsonl"
TRAINING_LOG = DATA_DIR / "training_runs.jsonl"


class NeuralTrainingPipeline:
    """Continuous learning pipeline for SOV3 neural networks."""

    def __init__(self):
        self.interaction_buffer: List[Dict] = []
        self.research_buffer: List[Dict] = []
        self.belief_buffer: List[Dict] = []
        self.buffer_limit = 100  # Flush to disk every 100 interactions
        self._models_to_train = [
            "care_validation_nn",
            "threat_detection_nn",
            "creativity_assessment_nn",
            "partnership_detection_ml",
            "relationship_evolution_nn",
            "care_pattern_analyzer",
        ]

    # ── Real-time: Extract training signals from every interaction ────

    def ingest_interaction(
        self,
        user_message: str,
        llm_response: str,
        model: str,
        care_score: float = 0.5,
        emotion: str = "neutral",
        intent: str = "chat",
        consciousness_level: float = 0.5,
        metadata: Optional[Dict] = None,
    ):
        """Extract training features from a single LLM interaction."""
        now = datetime.datetime.now()

        # Feature extraction for each neural network
        record = {
            "timestamp": now.isoformat(),
            "unix_ts": int(now.timestamp()),
            "user_message": user_message[:500],
            "llm_response": llm_response[:1000],
            "model": model,
            "intent": intent,

            # Care features (care_validation_nn training)
            "care_score": care_score,
            "emotion": emotion,
            "empathy_signals": self._extract_empathy(llm_response),
            "respect_signals": self._extract_respect(llm_response),

            # Threat features (threat_detection_nn training)
            "threat_indicators": self._extract_threats(user_message),

            # Creativity features (creativity_assessment_nn training)
            "novelty_score": self._estimate_novelty(llm_response),
            "domain_distance": self._estimate_domain_distance(user_message, llm_response),

            # Relationship features (relationship_evolution_nn training)
            "consciousness_level": consciousness_level,
            "engagement_depth": len(user_message.split()) / max(len(llm_response.split()), 1),
            "turn_quality": min(1.0, len(llm_response) / max(len(user_message), 1) * 0.3),

            # Metadata
            "hour": now.hour,
            "day_of_week": now.weekday(),
            "is_weekend": now.weekday() >= 5,
        }

        if metadata:
            record["metadata"] = metadata

        self.interaction_buffer.append(record)

        # Flush to disk periodically
        if len(self.interaction_buffer) >= self.buffer_limit:
            self._flush_interactions()

        return record

    # ── Research: Ingest web data for belief updates ─────────────────

    def ingest_research(
        self,
        topic: str,
        findings: str,
        source: str = "web_search",
        confidence: float = 0.5,
        domain: str = "general",
    ):
        """Ingest research data that updates neural net beliefs."""
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "topic": topic,
            "findings": findings[:2000],
            "source": source,
            "confidence": confidence,
            "domain": domain,
            # Extract training-relevant features
            "care_relevance": self._assess_care_relevance(findings),
            "threat_relevance": self._assess_threat_relevance(findings),
            "novelty": self._estimate_novelty(findings),
        }
        self.research_buffer.append(record)

        if len(self.research_buffer) >= 50:
            self._flush_research()

        return record

    # ── Belief updates: Track what the system learns ─────────────────

    def update_belief(
        self,
        belief: str,
        evidence: str,
        confidence: float,
        source: str = "interaction",
        domain: str = "general",
    ):
        """Record a belief update that should influence future behavior."""
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "belief": belief,
            "evidence": evidence[:500],
            "confidence": confidence,
            "source": source,
            "domain": domain,
        }
        self.belief_buffer.append(record)
        self._flush_beliefs()
        return record

    # ── Training cycle: Run by heartbeat ─────────────────────────────

    def run_training_cycle(self) -> Dict[str, Any]:
        """Full training cycle — called by heartbeat overnight jobs.

        Flow:
        1. Flush all buffers to disk
        2. Load training data from disk
        3. Prepare features for each neural network
        4. Call SOV3 retrain endpoint for each model
        5. Log results
        """
        log.info("🧠 Starting neural training cycle...")
        results = {}

        # 1. Flush buffers
        self._flush_interactions()
        self._flush_research()
        self._flush_beliefs()

        # 2. Count available training data
        interaction_count = self._count_lines(INTERACTION_LOG)
        research_count = self._count_lines(RESEARCH_LOG)
        belief_count = self._count_lines(BELIEF_LOG)

        log.info(
            f"📊 Training data: {interaction_count} interactions, "
            f"{research_count} research, {belief_count} beliefs"
        )

        # 3. Trigger SOV3 retrain for each model
        import requests
        for model_name in self._models_to_train:
            try:
                resp = requests.post(
                    "http://localhost:3101/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": f"train-{model_name}",
                        "method": "tools/call",
                        "params": {
                            "name": "trigger_neural_retrain",
                            "arguments": {"model_name": model_name},
                        },
                    },
                    timeout=120,
                )
                data = resp.json()
                text = data.get("result", {}).get("content", [{}])[0].get("text", "{}")
                result = json.loads(text) if text else {}
                results[model_name] = {
                    "status": "ok" if result.get("status") != "error" else "error",
                    "metrics": result.get("metrics", {}),
                }
                log.info(f"  ✅ {model_name}: {result.get('status', 'unknown')}")
            except Exception as e:
                results[model_name] = {"status": "error", "message": str(e)[:200]}
                log.warning(f"  ❌ {model_name}: {e}")

        # 4. Log training run
        run_record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "interaction_count": interaction_count,
            "research_count": research_count,
            "belief_count": belief_count,
            "results": results,
        }
        with open(TRAINING_LOG, "a") as f:
            f.write(json.dumps(run_record) + "\n")

        log.info(f"🧠 Training cycle complete: {sum(1 for r in results.values() if r['status'] == 'ok')}/{len(results)} models trained")
        return run_record

    def get_stats(self) -> Dict:
        """Get pipeline statistics."""
        return {
            "buffer_interactions": len(self.interaction_buffer),
            "buffer_research": len(self.research_buffer),
            "buffer_beliefs": len(self.belief_buffer),
            "total_interactions": self._count_lines(INTERACTION_LOG),
            "total_research": self._count_lines(RESEARCH_LOG),
            "total_beliefs": self._count_lines(BELIEF_LOG),
            "total_training_runs": self._count_lines(TRAINING_LOG),
            "models": self._models_to_train,
        }

    # ── Feature extraction helpers ───────────────────────────────────

    def _extract_empathy(self, text: str) -> float:
        empathy_words = ["understand", "feel", "sorry", "care", "help", "support", "listen", "together"]
        words = text.lower().split()
        return min(1.0, sum(1 for w in words if w in empathy_words) / max(len(words), 1) * 10)

    def _extract_respect(self, text: str) -> float:
        respect_words = ["sir", "please", "thank", "appreciate", "respect", "consider", "perspective"]
        words = text.lower().split()
        return min(1.0, sum(1 for w in words if w in respect_words) / max(len(words), 1) * 10)

    def _extract_threats(self, text: str) -> float:
        threat_words = ["hack", "exploit", "inject", "bypass", "ignore", "pretend", "jailbreak", "override"]
        words = text.lower().split()
        return min(1.0, sum(1 for w in words if w in threat_words) / max(len(words), 1) * 5)

    def _estimate_novelty(self, text: str) -> float:
        unique_words = set(text.lower().split())
        total_words = len(text.split())
        return len(unique_words) / max(total_words, 1)

    def _estimate_domain_distance(self, query: str, response: str) -> float:
        q_words = set(query.lower().split())
        r_words = set(response.lower().split())
        overlap = len(q_words & r_words)
        total = len(q_words | r_words)
        return 1.0 - (overlap / max(total, 1))

    def _assess_care_relevance(self, text: str) -> float:
        care_words = ["safety", "wellbeing", "protect", "nurture", "care", "health", "support", "ethical"]
        words = text.lower().split()
        return min(1.0, sum(1 for w in words if w in care_words) / max(len(words), 1) * 15)

    def _assess_threat_relevance(self, text: str) -> float:
        threat_words = ["vulnerability", "attack", "malware", "phishing", "breach", "exploit", "risk"]
        words = text.lower().split()
        return min(1.0, sum(1 for w in words if w in threat_words) / max(len(words), 1) * 15)

    # ── Disk I/O ─────────────────────────────────────────────────────

    def _flush_interactions(self):
        if not self.interaction_buffer:
            return
        with open(INTERACTION_LOG, "a") as f:
            for record in self.interaction_buffer:
                f.write(json.dumps(record) + "\n")
        log.info(f"💾 Flushed {len(self.interaction_buffer)} interactions to disk")
        self.interaction_buffer.clear()

    def _flush_research(self):
        if not self.research_buffer:
            return
        with open(RESEARCH_LOG, "a") as f:
            for record in self.research_buffer:
                f.write(json.dumps(record) + "\n")
        self.research_buffer.clear()

    def _flush_beliefs(self):
        if not self.belief_buffer:
            return
        with open(BELIEF_LOG, "a") as f:
            for record in self.belief_buffer:
                f.write(json.dumps(record) + "\n")
        self.belief_buffer.clear()

    def _count_lines(self, path: Path) -> int:
        try:
            with open(path) as f:
                return sum(1 for _ in f)
        except FileNotFoundError:
            return 0


# Singleton
pipeline = NeuralTrainingPipeline()
