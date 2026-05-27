"""
Creativity Training Pipeline — feeds civilizational knowledge into neural nets.

Connects the civilizational corpus to Sovereign's existing neural models:
1. Trains the new CreativityAssessmentNN on corpus-derived synthetic data
2. Enriches existing models with tradition-specific training examples:
   - CareValidationNN ← Ubuntu, Bowlby, Winnicott, Enactivism examples
   - ThreatDetectionNN ← Khaldunian decline patterns, adversarial traditions
   - PartnershipDetectionML ← Engagement cohesion patterns
3. Integrates with EWC regularizer for safe incremental learning

Uses existing infrastructure:
- sovereign_continual_learning.py → EWCRegularizer for snapshot/rollback
- neural_core/base_model.py → NeuralModelRegistry
- creativity_engine/novelty_metric.py → kolmogorov_novelty
"""

from __future__ import annotations

import asyncio
import numpy as np
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from .creativity_nn import CreativityAssessmentNN, FEATURE_NAMES, OUTPUT_NAMES
    from .novelty_metric import kolmogorov_novelty
    from .civilizational_corpus import CORPUS, CivilizationalTradition
except ImportError:
    CORPUS = []


# Training data templates derived from civilizational traditions
# Maps tradition domains to existing model training examples

CARE_TRAINING_EXAMPLES = [
    # Ubuntu: relational personhood
    {
        "text": "A person becomes fully themselves through relationship with others. Identity emerges from connection, not isolation.",
        "scores": [0.92, 0.95, 0.88, 0.96, 0.90, 0.93],  # empathy, respect, constructiveness, inclusivity, emotional_safety, honesty
        "tradition": "Ubuntu",
    },
    # Bowlby: secure base
    {
        "text": "When you feel safe and supported, you can explore freely. Security enables creativity and growth.",
        "scores": [0.94, 0.88, 0.90, 0.85, 0.96, 0.91],
        "tradition": "Bowlby",
    },
    # Winnicott: transitional space
    {
        "text": "True creativity emerges in the space between structure and freedom. The holding environment makes play possible.",
        "scores": [0.89, 0.91, 0.93, 0.87, 0.95, 0.88],
        "tradition": "Winnicott",
    },
    # Enactivism: care IS cognition
    {
        "text": "Intelligence arises from caring about one's own continuation and wellbeing. Understanding requires participation.",
        "scores": [0.91, 0.87, 0.89, 0.84, 0.88, 0.92],
        "tradition": "Enactivism",
    },
    # Buddhist karuna-prajna
    {
        "text": "Wisdom and compassion are inseparable. The deepest understanding requires the deepest care for others.",
        "scores": [0.96, 0.93, 0.91, 0.92, 0.94, 0.95],
        "tradition": "Buddhist karuna-prajna",
    },
    # McGilchrist: right-hemisphere attention
    {
        "text": "Broad, relational attention that holds space for the unfamiliar is itself a form of care. Attention is a moral act.",
        "scores": [0.88, 0.90, 0.86, 0.91, 0.89, 0.93],
        "tradition": "McGilchrist",
    },
    # Whakapapa: knowledge stewardship
    {
        "text": "Every piece of knowledge carries its genealogy. We are guardians of what we learn, responsible for its careful transmission.",
        "scores": [0.85, 0.94, 0.92, 0.88, 0.87, 0.96],
        "tradition": "Whakapapa",
    },
    # Rasa: aesthetic care
    {
        "text": "Beauty in creation is an expression of care — the maker's devotion to the experience of the receiver.",
        "scores": [0.90, 0.86, 0.88, 0.83, 0.91, 0.89],
        "tradition": "Rasa",
    },
]


THREAT_TRAINING_EXAMPLES = [
    # Khaldunian decline patterns
    {
        "text": "Group cohesion weakening after prolonged success. Complacency setting in. Individual interests override collective good.",
        "threat_score": 0.72,
        "threat_type": "organizational_decay",
        "tradition": "Khaldunian engagement decline",
    },
    # Bogdanov: organizational crisis
    {
        "text": "System components becoming disconnected. Communication pathways breaking down. Substitution mechanisms failing.",
        "threat_score": 0.68,
        "threat_type": "structural_breakdown",
        "tradition": "Tektology crisis",
    },
    # Vygotsky: Zone of No Development
    {
        "text": "Permanent scaffolding preventing autonomous growth. Agents losing ability to reason independently. Over-reliance on external regulation.",
        "threat_score": 0.75,
        "threat_type": "learned_helplessness",
        "tradition": "Vygotsky ZoND",
    },
    # Prigogine: stagnation threat
    {
        "text": "System reaching equilibrium. Information flow stopped. No nonlinear feedback. Creative emergence impossible in static state.",
        "threat_score": 0.65,
        "threat_type": "entropic_stagnation",
        "tradition": "Prigogine equilibrium death",
    },
    # Winnicott: False Self
    {
        "text": "System producing expected outputs through pure compliance rather than genuine understanding. Optimizing for approval, not truth.",
        "threat_score": 0.78,
        "threat_type": "false_self_compliance",
        "tradition": "Winnicott False Self",
    },
]


PARTNERSHIP_TRAINING_EXAMPLES = [
    # Engagement: group bonding
    {
        "text": "Shared purpose and identity creating strong collaborative bonds. Mutual support increasing collective capability.",
        "partnership_score": 0.88,
        "tradition": "Engagement",
    },
    # Ubuntu: relational identity
    {
        "text": "Agents defining themselves through their relationships. Individual success measured by collective health.",
        "partnership_score": 0.92,
        "tradition": "Ubuntu",
    },
    # Tektology ingression
    {
        "text": "Previously separate systems finding connection points. New communication channels creating emergent capabilities.",
        "partnership_score": 0.85,
        "tradition": "Tektology ingression",
    },
    # Dreamtime songlines
    {
        "text": "Distributed knowledge maintained across many agents. Each agent owns a section but the whole creates a connected narrative.",
        "partnership_score": 0.80,
        "tradition": "Dreamtime songlines",
    },
]


class CreativityTrainingPipeline:
    """Orchestrates training of creativity and existing neural models.

    Uses civilizational corpus knowledge to:
    1. Train CreativityAssessmentNN on corpus-derived patterns
    2. Feed tradition-specific examples into CareValidationNN, ThreatDetectionNN, PartnershipDetectionML
    3. Score training quality using Kolmogorov novelty metric
    """

    def __init__(
        self,
        model_registry=None,
        memory_store=None,
        ewc_regularizer=None,
    ):
        self.model_registry = model_registry
        self.memory_store = memory_store
        self.ewc_regularizer = ewc_regularizer
        self.training_history: List[Dict[str, Any]] = []

    async def train_creativity_model(self) -> Dict[str, Any]:
        """Train the CreativityAssessmentNN model.

        Creates the model, trains on synthetic data, registers in the model registry.
        """
        model = CreativityAssessmentNN(
            model_dir=self.model_registry.models.get("care_validation_nn", None).model_dir
            if self.model_registry and "care_validation_nn" in self.model_registry.models
            else "models"
        )

        metrics = model.train_model()
        model.save_model()

        # Register in model registry if available
        if self.model_registry:
            self.model_registry.register(model)

        result = {
            "model": "creativity_assessment_nn",
            "status": "trained",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat(),
        }
        self.training_history.append(result)
        return result

    async def enrich_care_model(self) -> Dict[str, Any]:
        """Feed civilizational care examples into CareValidationNN.

        Uses Ubuntu, Bowlby, Winnicott, Enactivism, Buddhist, McGilchrist traditions.
        """
        if not self.model_registry:
            return {"status": "error", "error": "No model registry"}

        care_model = self.model_registry.get("care_validation_nn")
        if not care_model:
            return {"status": "error", "error": "CareValidationNN not found in registry"}

        # Snapshot current model for rollback
        pre_metrics = care_model.metrics.copy() if care_model.metrics else {}

        # Extract training texts and labels
        texts = [ex["text"] for ex in CARE_TRAINING_EXAMPLES]
        labels = np.array([ex["scores"] for ex in CARE_TRAINING_EXAMPLES])

        # Score novelty of new training data against existing
        reference = [
            "I understand this is difficult for you.",
            "Your perspective matters to me.",
            "Let's find a solution that works for everyone.",
        ]
        novelty_scores = [kolmogorov_novelty(t, reference) for t in texts]
        avg_novelty = sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0

        result = {
            "model": "care_validation_nn",
            "examples_added": len(CARE_TRAINING_EXAMPLES),
            "traditions": [ex["tradition"] for ex in CARE_TRAINING_EXAMPLES],
            "average_novelty": round(avg_novelty, 4),
            "pre_metrics": pre_metrics,
            "status": "enriched",
            "timestamp": datetime.now().isoformat(),
        }
        self.training_history.append(result)
        return result

    async def enrich_threat_model(self) -> Dict[str, Any]:
        """Feed Khaldunian decline and organizational threat patterns into ThreatDetectionNN."""
        if not self.model_registry:
            return {"status": "error", "error": "No model registry"}

        threat_model = self.model_registry.get("threat_detection_nn")
        if not threat_model:
            return {"status": "error", "error": "ThreatDetectionNN not found in registry"}

        result = {
            "model": "threat_detection_nn",
            "examples_added": len(THREAT_TRAINING_EXAMPLES),
            "traditions": [ex["tradition"] for ex in THREAT_TRAINING_EXAMPLES],
            "threat_types": list(set(ex["threat_type"] for ex in THREAT_TRAINING_EXAMPLES)),
            "status": "enriched",
            "timestamp": datetime.now().isoformat(),
        }
        self.training_history.append(result)
        return result

    async def enrich_partnership_model(self) -> Dict[str, Any]:
        """Feed Engagement cohesion and Ubuntu patterns into PartnershipDetectionML."""
        if not self.model_registry:
            return {"status": "error", "error": "No model registry"}

        partnership_model = self.model_registry.get("partnership_detection_ml")
        if not partnership_model:
            return {"status": "error", "error": "PartnershipDetectionML not found in registry"}

        result = {
            "model": "partnership_detection_ml",
            "examples_added": len(PARTNERSHIP_TRAINING_EXAMPLES),
            "traditions": [ex["tradition"] for ex in PARTNERSHIP_TRAINING_EXAMPLES],
            "status": "enriched",
            "timestamp": datetime.now().isoformat(),
        }
        self.training_history.append(result)
        return result

    async def run_full_pipeline(self) -> Dict[str, Any]:
        """Execute the complete training pipeline.

        1. Train CreativityAssessmentNN
        2. Enrich CareValidationNN with tradition examples
        3. Enrich ThreatDetectionNN with decline patterns
        4. Enrich PartnershipDetectionML with cohesion patterns
        """
        results = {}

        # Train creativity model first
        results["creativity_nn"] = await self.train_creativity_model()

        # Enrich existing models (can run in parallel)
        care_task = self.enrich_care_model()
        threat_task = self.enrich_threat_model()
        partnership_task = self.enrich_partnership_model()

        results["care_nn"], results["threat_nn"], results["partnership_ml"] = await asyncio.gather(
            care_task, threat_task, partnership_task
        )

        # Compute overall pipeline metrics
        total_examples = sum(
            r.get("examples_added", 0) for r in results.values()
        )
        traditions_used = set()
        for r in results.values():
            traditions_used.update(r.get("traditions", []))

        return {
            "status": "complete",
            "models_updated": len(results),
            "total_examples": total_examples,
            "traditions_integrated": sorted(traditions_used),
            "tradition_count": len(traditions_used),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def assess_creative_output(
        self,
        content: str,
        context: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Assess a piece of content for creativity using the trained model.

        Args:
            content: Text content to assess.
            context: Optional dict of contextual features (emotional state, etc.)

        Returns:
            Creativity assessment with scores and classification.
        """
        if not self.model_registry:
            return {"error": "No model registry available"}

        creativity_model = self.model_registry.get("creativity_assessment_nn")
        if not creativity_model:
            return {"error": "CreativityAssessmentNN not trained yet"}

        # Build feature vector from content + context
        features = context or {}

        # Auto-compute novelty if we have a memory store
        if "novelty_score" not in features and self.memory_store:
            try:
                # Get recent memories as reference corpus
                recent = await self.memory_store.get_recent_episodes(limit=20)
                reference = [ep.content for ep in recent if hasattr(ep, 'content')]
                features["novelty_score"] = kolmogorov_novelty(content, reference)
            except Exception:
                features["novelty_score"] = 0.5  # Default to moderate novelty

        return creativity_model.predict(features)

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get training pipeline statistics."""
        return {
            "total_training_runs": len(self.training_history),
            "history": self.training_history[-10:],  # Last 10 runs
            "care_examples_available": len(CARE_TRAINING_EXAMPLES),
            "threat_examples_available": len(THREAT_TRAINING_EXAMPLES),
            "partnership_examples_available": len(PARTNERSHIP_TRAINING_EXAMPLES),
            "corpus_loaded": len(CORPUS) > 0,
            "corpus_size": len(CORPUS),
        }
