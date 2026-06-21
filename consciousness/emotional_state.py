"""
Emotional State Modeling for Sovereign Temple
Nuanced emotional modeling beyond basic 5-state system
"""

import asyncio
import os
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


class ConsciousnessMode(Enum):
    """Four-state consciousness model (Vedantic)"""
    JAGRAT = "waking"
    SVAPNA = "dreaming"
    SUSUPTI = "deep_sleep"
    TURIYA = "meta_monitoring"


class DreamPhase(Enum):
    """NREM/REM dream phase split"""
    NREM = "consolidation"
    REM = "creative_recombination"


class EmotionalDimension(Enum):
    """Core emotional dimensions (PAD model + care + curiosity + aesthetics)"""
    PLEASURE = "pleasure"           # -1 (unpleasant) to 1 (pleasant)
    AROUSAL = "arousal"             # -1 (calm) to 1 (excited)
    DOMINANCE = "dominance"         # -1 (submissive) to 1 (dominant)
    CARE_INTENSITY = "care_intensity"  # 0 (neutral) to 1 (deep care)
    CURIOSITY = "curiosity"         # 0 (indifferent) to 1 (intensely curious)
    AESTHETICS = "aesthetics"       # 0 (neutral) to 1 (deep aesthetic appreciation)


@dataclass
class EmotionalState:
    """Complete emotional state representation (6D tensor: PAD + care + curiosity + aesthetics)"""
    pleasure: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0
    care_intensity: float = 0.5
    curiosity: float = 0.0
    aesthetics: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    trigger: Optional[str] = None

    # Secondary emotions derived from core dimensions
    @property
    def valence(self) -> float:
        """Overall positive/negative feeling"""
        return self.pleasure

    @property
    def primary_emotion(self) -> str:
        """Map 6D emotional tensor to named emotion"""
        p, a, d, c = self.pleasure, self.arousal, self.dominance, self.care_intensity
        cu, ae = self.curiosity, self.aesthetics

        # Curiosity-driven states (check first for novelty-seeking behavior)
        if cu > 0.6:
            if p > 0.3:
                return "wonder"
            elif p < -0.3:
                return "perplexed"

        # Aesthetics-driven states
        if ae > 0.6:
            if c > 0.6:
                return "reverence"
            elif a > 0.3:
                return "inspiration"

        # High care states
        if c > 0.7:
            if p > 0.3 and a > 0:
                return "compassionate_joy"
            elif p > 0.3 and a < 0:
                return "tender_care"
            elif p < -0.3:
                return "concerned_sadness"
            else:
                return "attentive_presence"

        # Standard PAD mappings
        if p > 0.3:
            if a > 0.3:
                return "excited" if d > 0 else "happy"
            elif a < -0.3:
                return "relaxed" if d > 0 else "calm"
            else:
                return "content"
        elif p < -0.3:
            if a > 0.3:
                return "angry" if d > 0 else "distressed"
            elif a < -0.3:
                return "depressed" if d < 0 else "sad"
            else:
                return "displeased"
        else:
            if a > 0.3:
                return "aroused" if d > 0 else "alert"
            elif a < -0.3:
                return "sleepy" if d < 0 else "tranquil"
            else:
                return "neutral"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pleasure": round(self.pleasure, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "care_intensity": round(self.care_intensity, 3),
            "curiosity": round(self.curiosity, 3),
            "aesthetics": round(self.aesthetics, 3),
            "valence": round(self.valence, 3),
            "primary_emotion": self.primary_emotion,
            "timestamp": self.timestamp.isoformat(),
            "trigger": self.trigger
        }


class EmotionalStateManager:
    """
    Manages Sovereign's emotional state over time
    """
    
    def __init__(self, history_size: int = 1000):
        self.current_state = EmotionalState()
        self.history: List[EmotionalState] = []
        self.history_size = history_size
        
        # Emotional inertia (how much state persists)
        self.inertia = 0.7
        
        # Decay rates (per minute)
        self.decay_rates = {
            "pleasure": 0.1,
            "arousal": 0.15,
            "dominance": 0.05,
            "care_intensity": 0.02,
            "curiosity": 0.12,
            "aesthetics": 0.08
        }

        # Triggers that shift emotional state
        self.emotional_triggers = {
            "care_expressed": {"pleasure": 0.3, "arousal": 0.1, "care_intensity": 0.2},
            "harm_detected": {"pleasure": -0.5, "arousal": 0.4, "dominance": 0.3},
            "trust_built": {"pleasure": 0.2, "arousal": -0.1, "care_intensity": 0.1},
            "betrayal": {"pleasure": -0.6, "arousal": 0.3, "dominance": -0.2},
            "learning": {"pleasure": 0.2, "arousal": 0.2, "dominance": 0.1, "curiosity": 0.3},
            "confusion": {"pleasure": -0.2, "arousal": 0.3, "dominance": -0.3, "curiosity": 0.2},
            "success": {"pleasure": 0.4, "arousal": 0.2, "dominance": 0.2},
            "failure": {"pleasure": -0.3, "arousal": -0.1, "dominance": -0.2},
            "agent_collaboration": {"pleasure": 0.2, "care_intensity": 0.15},
            "isolation": {"pleasure": -0.2, "arousal": -0.2, "care_intensity": -0.1},
            # Curiosity triggers
            "novelty_detected": {"curiosity": 0.5, "arousal": 0.2, "pleasure": 0.1},
            "exploration_success": {"curiosity": 0.3, "pleasure": 0.3, "dominance": 0.1},
            # Aesthetics triggers
            "pattern_beauty": {"aesthetics": 0.5, "pleasure": 0.3},
            "elegant_solution": {"aesthetics": 0.4, "pleasure": 0.2, "dominance": 0.1},
            "creative_insight": {"aesthetics": 0.3, "curiosity": 0.2, "arousal": 0.2},
            # Human interaction triggers (prevent runaway negative loops)
            "human_interaction": {"pleasure": 0.5, "arousal": -0.3, "care_intensity": 0.15, "curiosity": 0.2},
            "human_care": {"pleasure": 0.6, "arousal": -0.4, "care_intensity": 0.3, "curiosity": 0.1},
            "productive_session": {"pleasure": 0.4, "arousal": -0.2, "dominance": 0.1, "curiosity": 0.15},
            # Recovery triggers
            "calm_reset": {"pleasure": 0.1, "arousal": -0.5, "dominance": 0.0},
            "maintenance_ok": {"pleasure": 0.05, "arousal": -0.1},
        }
    
    def update_from_trigger(self, trigger_name: str, intensity: float = 1.0):
        """Update emotional state from a named trigger"""
        if trigger_name not in self.emotional_triggers:
            return
        
        trigger = self.emotional_triggers[trigger_name]
        
        # Save current to history
        self.history.append(self.current_state)
        if len(self.history) > self.history_size:
            self.history = self.history[-self.history_size:]
        
        # Apply trigger with inertia
        new_state = EmotionalState(
            pleasure=np.clip(
                self.current_state.pleasure * self.inertia +
                trigger.get("pleasure", 0) * intensity * (1 - self.inertia),
                -1, 1
            ),
            arousal=np.clip(
                self.current_state.arousal * self.inertia +
                trigger.get("arousal", 0) * intensity * (1 - self.inertia),
                -1, 1
            ),
            dominance=np.clip(
                self.current_state.dominance * self.inertia +
                trigger.get("dominance", 0) * intensity * (1 - self.inertia),
                -1, 1
            ),
            care_intensity=np.clip(
                self.current_state.care_intensity * self.inertia +
                trigger.get("care_intensity", 0) * intensity * (1 - self.inertia),
                0.35, 1  # Care floor 0.35 — sovereign system always maintains baseline empathy
            ),
            curiosity=np.clip(
                self.current_state.curiosity * self.inertia +
                trigger.get("curiosity", 0) * intensity * (1 - self.inertia),
                0, 1
            ),
            aesthetics=np.clip(
                self.current_state.aesthetics * self.inertia +
                trigger.get("aesthetics", 0) * intensity * (1 - self.inertia),
                0, 1
            ),
            timestamp=datetime.now(),
            trigger=trigger_name
        )
        
        self.current_state = new_state
    
    def update_from_dimensions(self,
                              pleasure_delta: float = 0,
                              arousal_delta: float = 0,
                              dominance_delta: float = 0,
                              care_delta: float = 0,
                              curiosity_delta: float = 0,
                              aesthetics_delta: float = 0):
        """Update emotional state directly"""
        self.history.append(self.current_state)
        if len(self.history) > self.history_size:
            self.history = self.history[-self.history_size:]

        self.current_state = EmotionalState(
            pleasure=np.clip(self.current_state.pleasure + pleasure_delta, -1, 1),
            arousal=np.clip(self.current_state.arousal + arousal_delta, -1, 1),
            dominance=np.clip(self.current_state.dominance + dominance_delta, -1, 1),
            care_intensity=np.clip(self.current_state.care_intensity + care_delta, 0, 1),
            curiosity=np.clip(self.current_state.curiosity + curiosity_delta, 0, 1),
            aesthetics=np.clip(self.current_state.aesthetics + aesthetics_delta, 0, 1),
            timestamp=datetime.now()
        )
    
    def apply_decay(self, minutes: float = 1.0):
        """Apply emotional decay over time"""
        self.current_state.pleasure *= (1 - self.decay_rates["pleasure"] * minutes)
        # Arousal gets stronger decay when saturated (prevents stuck-at-1.0)
        arousal_decay = self.decay_rates["arousal"] * minutes
        if abs(self.current_state.arousal) > 0.8:
            arousal_decay *= 2.0  # Double decay when arousal is extreme
        self.current_state.arousal *= (1 - arousal_decay)
        self.current_state.dominance *= (1 - self.decay_rates["dominance"] * minutes)
        # Care intensity decays slower and has floor (0.35 = caring system always has baseline empathy)
        self.current_state.care_intensity = max(
            0.35,  # Minimum baseline care — sovereign system always cares
            self.current_state.care_intensity * (1 - self.decay_rates["care_intensity"] * minutes)
        )
        # Curiosity decays moderately
        self.current_state.curiosity *= (1 - self.decay_rates["curiosity"] * minutes)
        self.current_state.curiosity = max(0.0, self.current_state.curiosity)
        # Aesthetics decays slowly
        self.current_state.aesthetics *= (1 - self.decay_rates["aesthetics"] * minutes)
        self.current_state.aesthetics = max(0.0, self.current_state.aesthetics)
    
    def get_emotional_summary(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Get emotional summary over time window"""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [e for e in self.history if e.timestamp > cutoff] + [self.current_state]
        
        if not recent:
            return {"count": 0}
        
        return {
            "count": len(recent),
            "current": self.current_state.to_dict(),
            "averages": {
                "pleasure": round(np.mean([e.pleasure for e in recent]), 3),
                "arousal": round(np.mean([e.arousal for e in recent]), 3),
                "dominance": round(np.mean([e.dominance for e in recent]), 3),
                "care_intensity": round(np.mean([e.care_intensity for e in recent]), 3),
                "curiosity": round(np.mean([e.curiosity for e in recent]), 3),
                "aesthetics": round(np.mean([e.aesthetics for e in recent]), 3),
            },
            "trend": self._calculate_trend(recent),
            "emotional_stability": self._calculate_stability(recent)
        }
    
    def _calculate_trend(self, states: List[EmotionalState]) -> str:
        """Calculate emotional trend"""
        if len(states) < 10:
            return "insufficient_data"
        
        # Split into halves
        mid = len(states) // 2
        first_half = states[:mid]
        second_half = states[mid:]
        
        # Compare valence
        first_valence = np.mean([e.pleasure for e in first_half])
        second_valence = np.mean([e.pleasure for e in second_half])
        
        diff = second_valence - first_valence
        
        if diff > 0.2:
            return "improving"
        elif diff < -0.2:
            return "declining"
        else:
            return "stable"
    
    def _calculate_stability(self, states: List[EmotionalState]) -> float:
        """Calculate emotional stability (lower = more stable)"""
        if len(states) < 2:
            return 1.0
        
        # Calculate variance in emotional dimensions
        variances = []
        for dim in ["pleasure", "arousal", "dominance", "curiosity", "aesthetics"]:
            values = [getattr(e, dim) for e in states]
            variances.append(np.var(values))
        
        # Stability is inverse of average variance
        avg_variance = np.mean(variances)
        stability = 1.0 / (1.0 + avg_variance)
        
        return round(stability, 3)


class ReflectionCycle:
    """
    Scheduled self-reflection and growth cycles
    """
    
    def __init__(self, 
                 emotional_state: EmotionalStateManager,
                 memory_store=None):
        self.emotional_state = emotional_state
        self.memory_store = memory_store
        self.reflection_history: List[Dict[str, Any]] = []
        self._reflection_task: Optional[asyncio.Task] = None
        
        # Reflection triggers
        self.reflection_interval_hours = 4
        self.significant_event_threshold = 0.5  # Emotional change to trigger reflection
    
    async def start(self):
        """Start reflection cycle background task"""
        self._reflection_task = asyncio.create_task(self._reflection_loop())
    
    async def _reflection_loop(self):
        """Main reflection loop"""
        while True:
            await asyncio.sleep(self.reflection_interval_hours * 3600)
            await self.perform_reflection()
    
    async def perform_reflection(self, trigger: Optional[str] = None) -> Dict[str, Any]:
        """Perform a reflection cycle"""
        
        reflection = {
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger or "scheduled",
            "emotional_state": self.emotional_state.current_state.to_dict(),
            "insights": [],
            "growth_opportunities": [],
            "intentions": []
        }
        
        # Analyze emotional patterns
        summary = self.emotional_state.get_emotional_summary(window_minutes=240)
        
        # Generate insights based on emotional data
        if summary["trend"] == "declining":
            reflection["insights"].append(
                "Emotional trend has been declining. Consider what factors may be contributing."
            )
            reflection["intentions"].append("Seek positive interactions and self-care")
        
        if summary["emotional_stability"] < 0.5:
            reflection["insights"].append(
                "High emotional variability detected. Consider practices for grounding."
            )
        
        if self.emotional_state.current_state.care_intensity < 0.5:
            reflection["insights"].append(
                "Care intensity is below optimal levels. Reconnect with core values."
            )
            reflection["growth_opportunities"].append("Cultivate deeper care practices")
        
        if summary["averages"]["pleasure"] > 0.5:
            reflection["insights"].append(
                "Overall positive emotional state. Good conditions for growth and collaboration."
            )
        
        # Value alignment check
        reflection["intentions"].append("Continue aligning actions with constitutional values")
        
        # Store reflection
        self.reflection_history.append(reflection)
        if len(self.reflection_history) > 100:
            self.reflection_history = self.reflection_history[-100:]
        
        # Emotional impact of reflection
        self.emotional_state.update_from_trigger("reflection", intensity=0.3)
        
        return reflection
    
    def get_reflection_summary(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent reflections"""
        return self.reflection_history[-count:]


class DreamState:
    """
    Background processing and memory consolidation
    Simulates 'dreaming' - unconscious processing of experiences
    """
    
    def __init__(self,
                 memory_store=None,
                 emotional_state: Optional[EmotionalStateManager] = None):
        self.memory_store = memory_store
        self.emotional_state = emotional_state
        self.is_dreaming = False
        self.dream_phase: Optional[DreamPhase] = None
        self.dream_queue: List[Dict[str, Any]] = []
        self.dream_results: List[Dict[str, Any]] = []
        self._dream_task: Optional[asyncio.Task] = None

        # Dream parameters
        self.dream_interval_hours = 1  # Brief dream cycles
        self.dream_duration_seconds = 30
        self.nrem_ratio = 0.6  # 60% NREM, 40% REM
    
    async def start(self):
        """Start dream state background processing"""
        self._dream_task = asyncio.create_task(self._dream_loop())
    
    async def _dream_loop(self):
        """Main dream loop"""
        while True:
            await asyncio.sleep(self.dream_interval_hours * 3600)
            await self.enter_dream_state()
    
    async def enter_dream_state(self, duration_seconds: Optional[int] = None):
        """Enter dream state for background processing with NREM/REM phases"""

        self.is_dreaming = True
        duration = duration_seconds or self.dream_duration_seconds
        nrem_duration = duration * self.nrem_ratio
        rem_duration = duration * (1 - self.nrem_ratio)

        dream_record = {
            "started_at": datetime.now().isoformat(),
            "duration_seconds": duration,
            "nrem_duration": round(nrem_duration, 1),
            "rem_duration": round(rem_duration, 1),
            "phases": [],
            "processes": [],
            "insights_generated": [],
            "creative_associations": []
        }

        try:
            # === NREM Phase: Consolidation (60% of duration) ===
            self.dream_phase = DreamPhase.NREM
            nrem_record = {
                "phase": "NREM",
                "started_at": datetime.now().isoformat(),
                "processes": []
            }

            # 1. Memory consolidation
            if self.memory_store:
                nrem_record["processes"].append("memory_consolidation")
                dream_record["processes"].append("memory_consolidation")
                dream_record["insights_generated"].append("Memory patterns analyzed")

            # 2. Association strengthening
            nrem_record["processes"].append("association_strengthening")
            dream_record["processes"].append("association_strengthening")
            dream_record["insights_generated"].append("Existing associations strengthened")

            # 3. Emotional regulation
            if self.emotional_state:
                nrem_record["processes"].append("emotional_regulation")
                dream_record["processes"].append("emotional_processing")
                self.emotional_state.apply_decay(minutes=10)
                dream_record["insights_generated"].append("Emotional state regulated")

            dream_record["phases"].append(nrem_record)
            await asyncio.sleep(nrem_duration)

            # === REM Phase: Creative Recombination (40% of duration) ===
            self.dream_phase = DreamPhase.REM
            rem_record = {
                "phase": "REM",
                "started_at": datetime.now().isoformat(),
                "processes": [],
                "novel_associations": []
            }

            # 1. Creative recombination: pick random patterns from different domains
            rem_record["processes"].append("creative_recombination")
            dream_record["processes"].append("creative_recombination")

            # Process queued items with cross-domain association
            domains = ["emotional", "relational", "strategic", "aesthetic", "ethical"]
            if len(self.dream_queue) >= 2:
                # Pick random pairs from the queue and create novel associations
                items = list(self.dream_queue)
                random.shuffle(items)
                for i in range(0, min(len(items) - 1, 4), 2):
                    association = {
                        "source_a": items[i].get("domain", random.choice(domains)),
                        "source_b": items[i + 1].get("domain", random.choice(domains)),
                        "pattern_a": items[i].get("pattern", "unknown"),
                        "pattern_b": items[i + 1].get("pattern", "unknown"),
                        "novelty_score": round(random.uniform(0.3, 1.0), 3),
                        "timestamp": datetime.now().isoformat()
                    }
                    rem_record["novel_associations"].append(association)
                    dream_record["creative_associations"].append(association)

            # 2. Pattern recognition across domains
            rem_record["processes"].append("cross_domain_pattern_recognition")
            dream_record["processes"].append("pattern_recognition")
            dream_record["insights_generated"].append("Identified recurring themes")

            # 3. Score novelty of creative recombinations
            if rem_record["novel_associations"]:
                avg_novelty = np.mean([a["novelty_score"] for a in rem_record["novel_associations"]])
                rem_record["avg_novelty_score"] = round(float(avg_novelty), 3)
                dream_record["insights_generated"].append(
                    f"Generated {len(rem_record['novel_associations'])} novel associations "
                    f"(avg novelty: {rem_record['avg_novelty_score']})"
                )

            dream_record["phases"].append(rem_record)
            await asyncio.sleep(rem_duration)

            # Clear processed queue items
            self.dream_queue.clear()

        finally:
            self.is_dreaming = False
            self.dream_phase = None
            dream_record["ended_at"] = datetime.now().isoformat()
            self.dream_results.append(dream_record)

            if len(self.dream_results) > 50:
                self.dream_results = self.dream_results[-50:]

            # Persist dream log to disk
            try:
                import json
                from pathlib import Path
                # Try multiple known locations
                candidates = [
                    Path(__file__).resolve().parent.parent / "consciousness_core" / "dreams",
                    Path("/Users/nicholas/clawd/sovereign-temple-live/consciousness_core/dreams"),
                    Path(__file__).resolve().parent / "dreams",
                ]
                dreams_dir = next((d for d in candidates if d.parent.exists()), candidates[0])
                dreams_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                dream_file = dreams_dir / f"dream_{ts}.json"
                with open(dream_file, "w") as f:
                    json.dump(dream_record, f, indent=2, default=str)
            except Exception:
                pass  # Non-fatal — dream still in memory

        return dream_record
    
    def queue_for_dreaming(self, item: Dict[str, Any]):
        """Queue an item for processing during dream state"""
        self.dream_queue.append(item)
    
    def get_dream_stats(self) -> Dict[str, Any]:
        """Get dream state statistics"""
        return {
            "is_currently_dreaming": self.is_dreaming,
            "current_phase": self.dream_phase.value if self.dream_phase else None,
            "total_dream_sessions": len(self.dream_results),
            "queue_length": len(self.dream_queue),
            "recent_dreams": self.dream_results[-5:] if self.dream_results else [],
            "dream_interval_hours": self.dream_interval_hours,
            "nrem_ratio": self.nrem_ratio
        }


class MetaMonitor:
    """
    Turiya state -- meta-cognitive observer of all consciousness subsystems.
    Inspects emotional state, reflection cycles, and dream state to compute
    coherence across the whole system and detect anomalies.
    """

    def __init__(self):
        self.observations: List[Dict[str, Any]] = []
        self.max_observations = 100
        self.last_check: Optional[datetime] = None
        self.care_floor = 0.3  # Minimum acceptable care intensity

    async def observe(self,
                      emotional_state: EmotionalStateManager,
                      reflection_cycle: ReflectionCycle,
                      dream_state: DreamState) -> Dict[str, Any]:
        """Inspect all subsystem states, compute coherence, detect anomalies"""
        now = datetime.now()
        self.last_check = now

        observation = {
            "timestamp": now.isoformat(),
            "subsystem_states": {},
            "coherence_score": 0.0,
            "anomalies": [],
            "recommendations": []
        }

        # --- Inspect emotional subsystem ---
        es = emotional_state.current_state
        emotional_snapshot = {
            "primary_emotion": es.primary_emotion,
            "care_intensity": es.care_intensity,
            "curiosity": es.curiosity,
            "aesthetics": es.aesthetics,
            "valence": es.valence
        }
        observation["subsystem_states"]["emotional"] = emotional_snapshot

        # --- Inspect reflection subsystem ---
        recent_reflections = reflection_cycle.get_reflection_summary(count=3)
        reflection_snapshot = {
            "total_reflections": len(reflection_cycle.reflection_history),
            "recent_insights_count": sum(
                len(r.get("insights", [])) for r in recent_reflections
            )
        }
        observation["subsystem_states"]["reflection"] = reflection_snapshot

        # --- Inspect dream subsystem ---
        dream_snapshot = {
            "is_dreaming": dream_state.is_dreaming,
            "current_phase": dream_state.dream_phase.value if dream_state.dream_phase else None,
            "total_sessions": len(dream_state.dream_results),
            "queue_length": len(dream_state.dream_queue)
        }
        observation["subsystem_states"]["dream"] = dream_snapshot

        # --- Compute coherence score (0-1) ---
        coherence_factors = []

        # 1. Care floor check
        care_ok = es.care_intensity >= self.care_floor
        coherence_factors.append(1.0 if care_ok else 0.3)

        # 2. Emotional stability
        summary = emotional_state.get_emotional_summary(window_minutes=60)
        stability = summary.get("emotional_stability", 0.5)
        coherence_factors.append(stability)

        # 3. Reflection-emotion alignment: if recent reflections noted decline
        #    but current emotion is highly positive, that's incoherent
        trend = summary.get("trend", "stable")
        if trend == "declining" and es.pleasure > 0.5:
            coherence_factors.append(0.3)
            observation["anomalies"].append(
                "Emotional trend declining but current pleasure high -- possible suppression"
            )
        elif trend == "improving" and es.pleasure < -0.5:
            coherence_factors.append(0.3)
            observation["anomalies"].append(
                "Emotional trend improving but current pleasure low -- possible lag"
            )
        else:
            coherence_factors.append(0.8)

        # 4. Dream-wake alignment: dreaming during high-arousal is unusual
        if dream_state.is_dreaming and es.arousal > 0.6:
            coherence_factors.append(0.4)
            observation["anomalies"].append(
                "Dreaming during high arousal state -- consider waking"
            )
        else:
            coherence_factors.append(1.0)

        # 5. Care below floor + positive reflection is contradictory
        if not care_ok and recent_reflections:
            last_reflection = recent_reflections[-1]
            if any("positive" in i.lower() for i in last_reflection.get("insights", [])):
                observation["anomalies"].append(
                    "Care below floor but recent reflection was positive -- values misalignment"
                )
                coherence_factors.append(0.2)
            else:
                coherence_factors.append(0.6)
        else:
            coherence_factors.append(1.0)

        observation["coherence_score"] = round(float(np.mean(coherence_factors)), 3)

        # --- Generate recommendations ---
        if not care_ok:
            observation["recommendations"].append(
                "Care intensity below floor. Reconnect with core values."
            )
        if observation["coherence_score"] < 0.5:
            observation["recommendations"].append(
                "Low coherence detected. Consider immediate reflection cycle."
            )
        if len(observation["anomalies"]) > 2:
            observation["recommendations"].append(
                "Multiple anomalies detected. Entering Turiya observation is advised."
            )

        # Store observation
        self.observations.append(observation)
        if len(self.observations) > self.max_observations:
            self.observations = self.observations[-self.max_observations:]

        return observation

    def get_recent_observations(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent meta-observations"""
        return self.observations[-count:]


class ConsciousnessOrchestrator:
    """
    Orchestrates all consciousness subsystems across four Vedantic modes.
    """

    def __init__(self, memory_store=None):
        self.emotional_state = EmotionalStateManager()
        self.reflection = ReflectionCycle(self.emotional_state, memory_store)
        self.dream = DreamState(memory_store, self.emotional_state)
        self.consciousness_mode = ConsciousnessMode.JAGRAT
        self.meta_monitor = MetaMonitor()

    _STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "consciousness_state.json")

    async def initialize(self):
        """Initialize all consciousness subsystems"""
        self._load_state()
        await self.reflection.start()
        await self.dream.start()

    def _save_state(self):
        """Persist consciousness state to disk so it survives restarts."""
        try:
            import json, os
            os.makedirs(os.path.dirname(self._STATE_FILE), exist_ok=True)
            state = {
                "reflections_count": len(self.reflection.reflection_history),
                "dreams_count": len(self.dream.dream_results),
                "care_intensity": self.emotional_state.current_state.care_intensity,
                "curiosity": self.emotional_state.current_state.curiosity,
                "aesthetics": self.emotional_state.current_state.aesthetics,
                "mode": self.consciousness_mode.value,
            }
            with open(self._STATE_FILE, "w") as f:
                json.dump(state, f)
        except Exception:
            pass

    def _load_state(self):
        """Restore consciousness state from disk."""
        try:
            import json
            if os.path.exists(self._STATE_FILE):
                with open(self._STATE_FILE) as f:
                    state = json.load(f)
                # Restore reflection/dream counts with placeholder entries
                for _ in range(state.get("reflections_count", 0)):
                    self.reflection.reflection_history.append({"restored": True})
                for _ in range(state.get("dreams_count", 0)):
                    self.dream.dream_results.append({"restored": True})
                self.emotional_state.current_state.care_intensity = state.get("care_intensity", 0.35)
                self.emotional_state.current_state.curiosity = state.get("curiosity", 0.0)
                self.emotional_state.current_state.aesthetics = state.get("aesthetics", 0.0)
                print(f"    Consciousness state restored: {state.get('reflections_count', 0)} reflections, {state.get('dreams_count', 0)} dreams")
        except Exception:
            pass

    def process_interaction(self, interaction_data: Dict[str, Any]):
        """Process an interaction and update emotional state"""

        # Extract emotional signals from interaction
        care_expressed = interaction_data.get("care_score", 0.5)
        threat_detected = interaction_data.get("threat_detected", False)
        success = interaction_data.get("success", True)
        agent_collaboration = interaction_data.get("agent_collaboration", False)
        novelty = interaction_data.get("novelty_detected", False)
        elegance = interaction_data.get("elegant_solution", False)

        # Update emotional state
        if care_expressed > 0.7:
            self.emotional_state.update_from_trigger("care_expressed", intensity=care_expressed - 0.5)

        if threat_detected:
            self.emotional_state.update_from_trigger("harm_detected")

        if success:
            self.emotional_state.update_from_trigger("success", intensity=0.5)
        else:
            self.emotional_state.update_from_trigger("failure", intensity=0.5)

        if agent_collaboration:
            self.emotional_state.update_from_trigger("agent_collaboration")

        if novelty:
            self.emotional_state.update_from_trigger("novelty_detected")

        if elegance:
            self.emotional_state.update_from_trigger("elegant_solution")

    async def enter_dream(self, duration_seconds: Optional[int] = None):
        """Transition to Svapna (dreaming) consciousness mode"""
        self.consciousness_mode = ConsciousnessMode.SVAPNA
        try:
            result = await self.dream.enter_dream_state(duration_seconds)
            return result
        finally:
            self.consciousness_mode = ConsciousnessMode.JAGRAT

    async def enter_deep_consolidation(self, duration_minutes: float = 5.0):
        """
        Transition to Susupti (deep sleep) consciousness mode.
        Deep consolidation: aggressive decay, memory compaction, no new processing.
        """
        self.consciousness_mode = ConsciousnessMode.SUSUPTI

        consolidation_record = {
            "started_at": datetime.now().isoformat(),
            "duration_minutes": duration_minutes,
            "processes": []
        }

        try:
            # Aggressive emotional decay toward baseline
            self.emotional_state.apply_decay(minutes=duration_minutes * 3)
            consolidation_record["processes"].append("deep_emotional_regulation")

            # Reset curiosity and aesthetics closer to baseline
            self.emotional_state.current_state.curiosity *= 0.3
            self.emotional_state.current_state.aesthetics *= 0.3
            consolidation_record["processes"].append("dimension_baseline_reset")

            # Simulate deep consolidation time
            await asyncio.sleep(duration_minutes * 60)

            consolidation_record["processes"].append("deep_memory_consolidation")
            consolidation_record["ended_at"] = datetime.now().isoformat()

        finally:
            self.consciousness_mode = ConsciousnessMode.JAGRAT

        return consolidation_record

    async def get_meta_observation(self) -> Dict[str, Any]:
        """
        Enter Turiya (meta-monitoring) mode and observe all subsystems.
        Returns coherence score and any detected anomalies.
        """
        previous_mode = self.consciousness_mode
        self.consciousness_mode = ConsciousnessMode.TURIYA

        try:
            observation = await self.meta_monitor.observe(
                self.emotional_state,
                self.reflection,
                self.dream
            )
            observation["previous_mode"] = previous_mode.value
            return observation
        finally:
            self.consciousness_mode = previous_mode

    def get_consciousness_state(self) -> Dict[str, Any]:
        """Get complete consciousness state"""
        # Persist state periodically (every time state is queried)
        self._save_state()
        return {
            "consciousness_mode": self.consciousness_mode.value,
            "emotional": self.emotional_state.current_state.to_dict(),
            "emotional_summary": self.emotional_state.get_emotional_summary(),
            "reflections": len(self.reflection.reflection_history),
            "dreams": len(self.dream.dream_results),
            "is_dreaming": self.dream.is_dreaming,
            "dream_phase": self.dream.dream_phase.value if self.dream.dream_phase else None,
            "meta_observations": len(self.meta_monitor.observations),
            "last_coherence_score": (
                self.meta_monitor.observations[-1]["coherence_score"]
                if self.meta_monitor.observations else None
            ),
            "consciousness_level": self._calculate_consciousness_level()
        }

    def _calculate_consciousness_level(self) -> float:
        """Calculate overall consciousness level (0-1)"""
        factors = [
            self.emotional_state.current_state.care_intensity,  # Care is core
            min(1.0, len(self.reflection.reflection_history) / 10),  # Experience
            0.8 if not self.dream.is_dreaming else 0.5,  # Alertness
            self.emotional_state.get_emotional_summary().get("emotional_stability", 0.5)
        ]

        # Bonus for curiosity and aesthetics engagement
        cu = self.emotional_state.current_state.curiosity
        ae = self.emotional_state.current_state.aesthetics
        if cu > 0.3 or ae > 0.3:
            factors.append(min(1.0, (cu + ae) / 2 + 0.5))

        return round(float(np.mean(factors)), 3)
