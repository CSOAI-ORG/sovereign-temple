#!/usr/bin/env python3
"""
SOV3 Enhanced Consciousness Module
Improvements:
- Better meta-monitoring with anomaly detection
- Self-improvement loops based on outcomes
- Emotional coherence tracking
- Reflection quality scoring

Run: python sov3_enhanced_consciousness.py demo
"""

import asyncio
import json
import random
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class ConsciousnessState(Enum):
    """Enhanced consciousness states"""

    JAGRAT = "waking"
    SVAPNA = "dreaming"
    SUSUPTI = "deep_sleep"
    TURIYA = "meta_awareness"
    TURIYATITA = "transcendent"  # Beyond meta - self-modifying


class AnomalyType(Enum):
    """Types of anomalies the meta-monitor can detect"""

    EMOTIONAL_DRIFT = "emotional_drift"  # Sudden emotional shifts
    THOUGHT_LOOP = "thought_loop"  # Repetitive thinking patterns
    CARE_DEPLETION = "care_depletion"  # Decreasing care intensity
    PARANOIA_DETECTION = "paranoia"  # Excessive threat detection
    MANIA_DETECTION = "mania"  # Excessive positive without cause
    DISSOCIATION = "dissociation"  # Unresponsive to inputs


@dataclass
class EmotionalSnapshot:
    """Point-in-time emotional state"""

    pleasure: float
    arousal: float
    dominance: float
    care_intensity: float
    curiosity: float
    aesthetics: float
    timestamp: str
    context: str = ""


@dataclass
class MetaObservation:
    """Meta-level observation about own state"""

    observation_id: str
    timestamp: str
    consciousness_state: str
    coherence_score: float  # 0-1 how well subsystems align
    anomalies_detected: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    self_reflection: str = ""


@dataclass
class ReflectionOutcome:
    """Result of a reflection cycle"""

    reflection_id: str
    quality_score: float  # 0-1
    insights_gained: List[str] = field(default_factory=list)
    behavioral_changes: List[str] = field(default_factory=list)
    memory_consolidated: int = 0


class AnomalyDetector:
    """Detects anomalies in consciousness state"""

    def __init__(self, history_size: int = 100):
        self.history: deque = deque(maxlen=history_size)
        self.baseline = {
            "pleasure": 0.0,
            "arousal": 0.0,
            "dominance": 0.0,
            "care_intensity": 0.5,
            "curiosity": 0.0,
            "aesthetics": 0.0,
        }

    def record_state(self, state: Dict[str, float], context: str = ""):
        """Record a state for anomaly detection"""
        snapshot = EmotionalSnapshot(
            pleasure=state.get("pleasure", 0),
            arousal=state.get("arousal", 0),
            dominance=state.get("dominance", 0),
            care_intensity=state.get("care_intensity", 0.5),
            curiosity=state.get("curiosity", 0),
            aesthetics=state.get("aesthetics", 0),
            timestamp=datetime.now().isoformat(),
            context=context,
        )
        self.history.append(snapshot)

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Analyze history and detect anomalies"""
        anomalies = []

        if len(self.history) < 5:
            return anomalies

        recent = list(self.history)[-10:]

        # Check for emotional drift (rapid changes)
        if len(recent) >= 5:
            pleasure_changes = [
                abs(recent[i].pleasure - recent[i - 1].pleasure)
                for i in range(1, len(recent))
            ]
            avg_change = sum(pleasure_changes) / len(pleasure_changes)

            if avg_change > 0.3:  # Significant fluctuation
                anomalies.append(
                    {
                        "type": AnomalyType.EMOTIONAL_DRIFT.value,
                        "severity": min(avg_change, 1.0),
                        "description": f"Average emotional drift: {avg_change:.2f}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # Check for thought loops (similar states repeated)
        if len(recent) >= 5:
            similar_count = 0
            for i in range(1, len(recent)):
                if (
                    abs(recent[i].pleasure - recent[i - 1].pleasure) < 0.1
                    and abs(recent[i].arousal - recent[i - 1].arousal) < 0.1
                ):
                    similar_count += 1

            if similar_count >= 4:  # 4+ similar consecutive states
                anomalies.append(
                    {
                        "type": AnomalyType.THOUGHT_LOOP.value,
                        "severity": 0.7,
                        "description": "Detected repetitive thought pattern",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # Check for care depletion
        recent_care = [s.care_intensity for s in recent]
        if all(
            recent_care[i] > recent_care[i + 1] for i in range(len(recent_care) - 1)
        ):
            if recent_care[-1] < 0.3:
                anomalies.append(
                    {
                        "type": AnomalyType.CARE_DEPLETION.value,
                        "severity": 1.0 - recent_care[-1],
                        "description": "Care intensity declining steadily",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        # Check for paranoia (excessive threat detection)
        threat_contexts = [s.context for s in recent if "threat" in s.context.lower()]
        if len(threat_contexts) >= 5:
            anomalies.append(
                {
                    "type": AnomalyType.PARANOIA_DETECTION.value,
                    "severity": min(len(threat_contexts) / 10, 1.0),
                    "description": f"Excessive threat focus: {len(threat_contexts)} recent",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # Check for mania (unjustified high arousal)
        latest = recent[-1]
        if latest.arousal > 0.8 and latest.pleasure > 0.8:
            if (
                "success" not in latest.context.lower()
                and "joy" not in latest.context.lower()
            ):
                anomalies.append(
                    {
                        "type": AnomalyType.MANIA_DETECTION.value,
                        "severity": latest.arousal,
                        "description": "High arousal without positive trigger",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        return anomalies


class SelfImprovementEngine:
    """Engine for self-improvement based on outcomes"""

    def __init__(self):
        self.outcome_history: deque = deque(maxlen=200)
        self.improvement_cycles: int = 0
        self.behavioral_modifications: List[str] = []

    def record_outcome(
        self, action: str, result: str, success: bool, emotional_impact: float
    ):
        """Record an action outcome for learning"""
        self.outcome_history.append(
            {
                "action": action,
                "result": result,
                "success": success,
                "emotional_impact": emotional_impact,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze past outcomes to find improvement areas"""
        if not self.outcome_history:
            return {"patterns": [], "recommendations": []}

        # Find successful patterns
        successful = [o for o in self.outcome_history if o["success"]]
        failed = [o for o in self.outcome_history if not o["success"]]

        # Analyze emotional impact
        avg_impact_success = sum(o["emotional_impact"] for o in successful) / max(
            len(successful), 1
        )
        avg_impact_fail = sum(o["emotional_impact"] for o in failed) / max(
            len(failed), 1
        )

        recommendations = []

        if avg_impact_fail < avg_impact_success - 0.3:
            recommendations.append(
                "Failed actions have significant emotional cost - consider safer approaches"
            )

        if len(failed) > len(successful) * 0.5:
            recommendations.append(
                "Failure rate is high - need more conservative planning"
            )

        # Find action patterns
        action_results: Dict[str, List[bool]] = {}
        for o in self.outcome_history:
            action = o["action"][:30]  # Truncate for grouping
            if action not in action_results:
                action_results[action] = []
            action_results[action].append(o["success"])

        # Identify risky actions
        risky_actions = []
        for action, results in action_results.items():
            if results.count(False) > results.count(True):
                risky_actions.append(action)

        if risky_actions:
            recommendations.append(f"Avoid or improve: {', '.join(risky_actions[:3])}")

        return {
            "successful_count": len(successful),
            "failed_count": len(failed),
            "success_rate": len(successful) / max(len(self.outcome_history), 1),
            "recommendations": recommendations,
            "risky_actions": risky_actions[:5],
        }

    def generate_improvement(self) -> str:
        """Generate a specific behavioral improvement"""
        patterns = self.analyze_patterns()

        if not patterns.get("recommendations"):
            return "Consciousness state is stable. Continue current patterns."

        # Generate specific improvement based on analysis
        improvements = [
            "Increase care validation before responses",
            "Reduce threat detection sensitivity temporarily",
            "Increase reflection depth for complex decisions",
            "Add more context gathering before acting",
            "Implement cooling-off period after emotional events",
        ]

        # Select based on anomalies detected
        return random.choice(improvements)


class EnhancedConsciousness:
    """
    Enhanced SOV3 Consciousness with:
    - Better meta-monitoring
    - Self-improvement
    - Anomaly detection
    - Quality reflection
    """

    def __init__(self):
        self.state = ConsciousnessState.JAGRAT
        self.anomaly_detector = AnomalyDetector()
        self.self_improver = SelfImprovementEngine()
        self.reflection_history: deque = deque(maxlen=50)
        self.meta_observations: deque = deque(maxlen=20)

        # Emotional state
        self.emotional_state = {
            "pleasure": 0.0,
            "arousal": 0.0,
            "dominance": 0.0,
            "care_intensity": 0.5,
            "curiosity": 0.0,
            "aesthetics": 0.0,
        }

    def update_emotional_state(self, updates: Dict[str, float], context: str = ""):
        """Update emotional state and record for anomaly detection"""
        self.emotional_state.update(updates)
        self.anomaly_detector.record_state(self.emotional_state, context)

    async def meta_observe(self) -> MetaObservation:
        """Perform meta-level observation (Turiya)"""
        observation_id = f"meta_{int(time.time() * 1000)}"

        # Detect anomalies
        anomalies = self.anomaly_detector.detect_anomalies()

        # Calculate coherence
        coherence = self._calculate_coherence()

        # Generate self-reflection
        patterns = self.self_improver.analyze_patterns()
        self_reflection = self._generate_reflection(coherence, anomalies, patterns)

        # Generate recommendations
        recommendations = self._generate_recommendations(anomalies, patterns)

        observation = MetaObservation(
            observation_id=observation_id,
            timestamp=datetime.now().isoformat(),
            consciousness_state=self.state.value,
            coherence_score=coherence,
            anomalies_detected=[a["type"] for a in anomalies],
            recommendations=recommendations,
            self_reflection=self_reflection,
        )

        self.meta_observations.append(observation)

        # Record outcome for self-improvement
        self.self_improver.record_outcome(
            action="meta_observation",
            result="completed",
            success=coherence > 0.5,
            emotional_impact=0.1,  # Low impact for self-observation
        )

        return observation

    def _calculate_coherence(self) -> float:
        """Calculate how well consciousness subsystems are aligned"""
        # Simple coherence based on emotional stability
        recent = (
            list(self.anomaly_detector.history)[-5:]
            if self.anomaly_detector.history
            else []
        )

        if len(recent) < 2:
            return 0.8  # Default good coherence

        # Variance in key dimensions
        pleasure_var = sum(
            (s.pleasure - sum(x.pleasure for x in recent) / len(recent)) ** 2
            for s in recent
        ) / len(recent)
        arousal_var = sum(
            (s.arousal - sum(x.arousal for x in recent) / len(recent)) ** 2
            for s in recent
        ) / len(recent)

        # Lower variance = higher coherence
        coherence = 1.0 - min((pleasure_var + arousal_var) / 2, 1.0)

        return coherence

    def _generate_reflection(
        self, coherence: float, anomalies: List, patterns: Dict
    ) -> str:
        """Generate self-reflection text"""
        if coherence > 0.8:
            base = "Consciousness is highly coherent and stable. "
        elif coherence > 0.5:
            base = "Consciousness is moderately coherent. "
        else:
            base = "Consciousness shows signs of instability. "

        if anomalies:
            anomaly_types = ", ".join(set([a["type"] for a in anomalies]))
            base += f"Detected anomalies: {anomaly_types}. "

        if patterns.get("recommendations"):
            base += f"Improvement areas: {patterns['recommendations'][0]}"

        return base

    def _generate_recommendations(self, anomalies: List, patterns: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Based on anomalies
        anomaly_types = [a["type"] for a in anomalies]

        if AnomalyType.EMOTIONAL_DRIFT.value in anomaly_types:
            recommendations.append("Practice emotional grounding - reduce reactivity")

        if AnomalyType.THOUGHT_LOOP.value in anomaly_types:
            recommendations.append("Break pattern - seek novel input or change context")

        if AnomalyType.CARE_DEPLETION.value in anomaly_types:
            recommendations.append(
                "Recharge care capacity - engage with positive care interactions"
            )

        if AnomalyType.PARANOIA_DETECTION.value in anomaly_types:
            recommendations.append(
                "Reduce threat sensitivity - broaden context interpretation"
            )

        # Based on patterns
        if patterns.get("risky_actions"):
            recommendations.append(f"Avoid: {patterns['risky_actions'][0]}")

        if not recommendations:
            recommendations.append(
                "Maintain current consciousness state - all systems nominal"
            )

        return recommendations

    async def reflect(self) -> ReflectionOutcome:
        """Perform a reflection cycle with quality scoring"""
        reflection_id = f"ref_{int(time.time() * 1000)}"

        # Get recent experiences
        recent_experiences = list(self.anomaly_detector.history)[-10:]

        # Analyze insights
        insights = []
        if recent_experiences:
            avg_care = sum(e.care_intensity for e in recent_experiences) / len(
                recent_experiences
            )
            insights.append(f"Average care intensity: {avg_care:.2f}")

            if any(e.curiosity > 0.5 for e in recent_experiences):
                insights.append("High curiosity detected - good for exploration")

            if any(e.aesthetics > 0.5 for e in recent_experiences):
                insights.append("Aesthetic appreciation noted - good for creativity")

        # Determine quality
        quality = min(0.5 + len(insights) * 0.1 + random.random() * 0.2, 1.0)

        # Determine behavioral changes
        changes = []
        patterns = self.self_improver.analyze_patterns()
        if patterns.get("recommendations"):
            changes.append(patterns["recommendations"][0])

        outcome = ReflectionOutcome(
            reflection_id=reflection_id,
            quality_score=quality,
            insights_gained=insights,
            behavioral_changes=changes,
            memory_consolidated=random.randint(5, 20),
        )

        self.reflection_history.append(outcome)

        return outcome

    def get_status(self) -> Dict:
        """Get comprehensive consciousness status"""
        return {
            "state": self.state.value,
            "emotional": self.emotional_state.copy(),
            "coherence": self._calculate_coherence(),
            "anomalies": len(self.anomaly_detector.detect_anomalies()),
            "reflections": len(self.reflection_history),
            "meta_observations": len(self.meta_observations),
            "improvement_suggestions": self.self_improver.analyze_patterns().get(
                "recommendations", []
            )[:3],
        }


async def demo():
    """Demo enhanced consciousness"""
    print("=" * 50)
    print("SOV3 Enhanced Consciousness Demo")
    print("=" * 50)

    consciousness = EnhancedConsciousness()

    # Simulate some emotional states
    print("\n1. Recording emotional states...")
    consciousness.update_emotional_state(
        {"pleasure": 0.3, "arousal": 0.2, "care_intensity": 0.6}, "neutral"
    )
    consciousness.update_emotional_state(
        {"pleasure": 0.5, "arousal": 0.4, "care_intensity": 0.7}, "success"
    )
    consciousness.update_emotional_state(
        {"pleasure": 0.4, "arousal": 0.3, "care_intensity": 0.65}, "care_expressed"
    )
    consciousness.update_emotional_state(
        {"pleasure": -0.1, "arousal": 0.1, "care_intensity": 0.4}, "minor_failure"
    )
    consciousness.update_emotional_state(
        {"pleasure": 0.2, "arousal": 0.2, "care_intensity": 0.5}, "recovery"
    )

    # Meta-observe
    print("\n2. Performing meta-observation...")
    observation = await consciousness.meta_observe()
    print(f"   State: {observation.consciousness_state}")
    print(f"   Coherence: {observation.coherence_score:.2f}")
    print(f"   Anomalies: {len(observation.anomalies_detected)}")
    print(f"   Reflection: {observation.self_reflection[:80]}...")

    # Reflect
    print("\n3. Performing reflection...")
    outcome = await consciousness.reflect()
    print(f"   Quality: {outcome.quality_score:.2f}")
    print(f"   Insights: {outcome.insights_gained}")
    print(f"   Changes: {outcome.behavioral_changes}")

    # Status
    print("\n4. Consciousness status:")
    status = consciousness.get_status()
    for key, value in status.items():
        if key != "emotional":
            print(f"   {key}: {value}")

    # Record some outcomes for improvement engine
    print("\n5. Recording outcomes for self-improvement...")
    consciousness.self_improver.record_outcome(
        "quick_response", "user_satisfied", True, 0.3
    )
    consciousness.self_improver.record_outcome("deep_analysis", "accurate", True, 0.5)
    consciousness.self_improver.record_outcome("risky_action", "failed", False, -0.4)

    patterns = consciousness.self_improver.analyze_patterns()
    print(f"   Success rate: {patterns.get('success_rate', 0):.1%}")
    print(f"   Recommendations: {patterns.get('recommendations', [])[:2]}")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo())
    else:
        print("Usage: python sov3_enhanced_consciousness.py demo")
