#!/usr/bin/env python3
"""
SOV3 Continual Learning Module
Features:
- Elastic Weight Consolidation (EWC) for catastrophic forgetting prevention
- Online learning with feedback incorporation
- Multi-task learning support
- Learning rate adaptation based on task similarity

Run: python sov3_continual_learning.py demo
"""

import json
import numpy as np
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import random


@dataclass
class TaskExample:
    """Training example for a specific task"""

    input_data: Any
    target: Any
    task_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class LearnedPattern:
    """Pattern learned from examples"""

    pattern_id: str
    task_name: str
    features: Dict[str, float]
    confidence: float
    learned_at: str
    last_used: str
    usage_count: int = 0


class ElasticWeightConsolidation:
    """
    EWC implementation to prevent catastrophic forgetting
    Keeps important parameters from previous tasks
    """

    def __init__(self, lambda_ewc: float = 1000):
        self.lambda_ewc = lambda_ewc  # EWC penalty weight
        self.fisher_information: Dict[str, np.ndarray] = {}
        self.optimal_params: Dict[str, np.ndarray] = {}
        self.task_count = 0

    def compute_fisher_diagonal(self, examples: List[TaskExample]) -> Dict[str, float]:
        """
        Compute diagonal Fisher information matrix
        Estimates parameter importance for each task
        """
        # Simplified Fisher computation
        fisher = {}

        # Estimate feature importance from examples
        feature_counts = defaultdict(float)

        for example in examples:
            if hasattr(example.input_data, "keys"):
                for key, value in example.input_data.items():
                    if isinstance(value, (int, float)):
                        feature_counts[key] += abs(value)

        # Normalize
        total = sum(feature_counts.values()) or 1
        for key in feature_counts:
            feature_counts[key] /= total

        return dict(feature_counts)

    def register_task(
        self, task_name: str, examples: List[TaskExample], params: Dict[str, Any]
    ):
        """Register a new task and its optimal parameters"""
        self.task_count += 1

        # Compute Fisher information for this task
        self.fisher_information[task_name] = self.compute_fisher_diagonal(examples)

        # Store current parameters as optimal for this task
        self.optimal_params[task_name] = params

        print(f"[EWC] Registered task: {task_name} with {len(examples)} examples")

    def compute_ewc_penalty(self, current_params: Dict[str, Any]) -> float:
        """Compute EWC penalty for current parameters"""
        penalty = 0.0

        for task_name, optimal in self.optimal_params.items():
            fisher = self.fisher_information.get(task_name, {})

            for key, value in current_params.items():
                if key in optimal and key in fisher:
                    diff = value - optimal[key]
                    importance = fisher[key]
                    penalty += importance * (diff**2)

        return penalty * self.lambda_ewc

    def get_ewc_loss(self, current_params: Dict[str, Any]) -> Dict[str, float]:
        """Get detailed EWC loss breakdown"""
        return {
            "penalty": self.compute_ewc_penalty(current_params),
            "tasks_registered": self.task_count,
            "task_names": list(self.optimal_params.keys()),
        }


class OnlineLearningEngine:
    """
    Online learning with feedback incorporation
    """

    def __init__(self):
        self.patterns: Dict[str, LearnedPattern] = {}
        self.feedback_history: List[Dict] = []
        self.adaptation_rate = 0.1

    def learn_from_feedback(
        self,
        prediction: Any,
        actual: Any,
        context: Dict,
        feedback_type: str,  # "correct", "incorrect", "partial"
    ):
        """Learn from feedback on predictions"""
        feedback_entry = {
            "prediction": str(prediction)[:100],
            "actual": str(actual)[:100],
            "feedback_type": feedback_type,
            "context": {k: str(v)[:50] for k, v in context.items()},
            "timestamp": datetime.now().isoformat(),
        }
        self.feedback_history.append(feedback_entry)

        # Update pattern confidence based on feedback
        if feedback_type == "correct":
            self._increase_confidence(context, 0.1)
        elif feedback_type == "incorrect":
            self._decrease_confidence(context, 0.2)
        elif feedback_type == "partial":
            self._adjust_confidence(context, 0.05)

        # Keep only last 1000 feedback entries
        if len(self.feedback_history) > 1000:
            self.feedback_history = self.feedback_history[-1000:]

    def _increase_confidence(self, context: Dict, amount: float):
        """Increase confidence for matching patterns"""
        for pattern in self.patterns.values():
            match = sum(
                1
                for k, v in context.items()
                if k in pattern.features and pattern.features[k] == v
            )
            if match > 0:
                pattern.confidence = min(1.0, pattern.confidence + amount * match)
                pattern.usage_count += 1

    def _decrease_confidence(self, context: Dict, amount: float):
        """Decrease confidence for incorrect patterns"""
        for pattern in self.patterns.values():
            match = sum(
                1
                for k, v in context.items()
                if k in pattern.features and pattern.features[k] == v
            )
            if match > 0:
                pattern.confidence = max(0.0, pattern.confidence - amount * match)

    def _adjust_confidence(self, context: Dict, amount: float):
        """Slightly adjust confidence"""
        self._increase_confidence(context, amount / 2)

    def get_adapted_prediction(self, context: Dict) -> Optional[str]:
        """Get prediction adapted based on recent feedback"""
        if not self.patterns:
            return None

        # Find best matching pattern
        best_pattern = None
        best_match = 0

        for pattern in self.patterns.values():
            match = sum(
                1
                for k, v in context.items()
                if k in pattern.features and pattern.features[k] == v
            )
            if match > best_match:
                best_match = match
                best_pattern = pattern

        if best_pattern and best_pattern.confidence > 0.3:
            best_pattern.last_used = datetime.now().isoformat()
            return f"pattern_{best_pattern.pattern_id}"

        return None

    def get_learning_stats(self) -> Dict:
        """Get learning statistics"""
        return {
            "total_patterns": len(self.patterns),
            "feedback_count": len(self.feedback_history),
            "correct_feedback": sum(
                1 for f in self.feedback_history if f["feedback_type"] == "correct"
            ),
            "incorrect_feedback": sum(
                1 for f in self.feedback_history if f["feedback_type"] == "incorrect"
            ),
            "avg_confidence": np.mean([p.confidence for p in self.patterns.values()])
            if self.patterns
            else 0,
        }


class ContinualLearningManager:
    """
    Main continual learning manager combining EWC and online learning
    """

    def __init__(self):
        self.ewc = ElasticWeightConsolidation(lambda_ewc=500)
        self.online = OnlineLearningEngine()
        self.task_performance: Dict[str, List[float]] = defaultdict(list)

    def train_on_task(
        self,
        task_name: str,
        examples: List[TaskExample],
        initial_params: Dict[str, Any],
    ) -> Dict[str, float]:
        """Train on a new task while preserving previous knowledge"""

        # Register with EWC
        self.ewc.register_task(task_name, examples, initial_params)

        # Simulate training (in production would be actual neural network training)
        final_params = initial_params.copy()
        for key in final_params:
            if isinstance(final_params[key], (int, float)):
                final_params[key] += random.uniform(-0.1, 0.1)

        # Compute final EWC penalty
        ewc_result = self.ewc.get_ewc_loss(final_params)

        return {
            "task": task_name,
            "examples_processed": len(examples),
            "ewc_penalty": ewc_result["penalty"],
            "total_tasks": ewc_result["tasks_registered"],
        }

    def learn_from_interaction(self, interaction: Dict, outcome: Dict):
        """Learn from a single interaction"""
        prediction = interaction.get("prediction", "")
        actual = outcome.get("result", "")
        correct = outcome.get("correct", False)

        feedback_type = (
            "correct"
            if correct
            else ("partial" if outcome.get("partial", False) else "incorrect")
        )

        self.online.learn_from_feedback(
            prediction=prediction,
            actual=actual,
            context=interaction.get("context", {}),
            feedback_type=feedback_type,
        )

    def get_training_recommendation(self, task_name: str) -> Dict[str, Any]:
        """Get recommendation for training approach based on task similarity"""
        existing_tasks = list(self.ewc.optimal_params.keys())

        if not existing_tasks:
            return {
                "approach": "fresh",  # No prior knowledge, train from scratch
                "rationale": "No previous tasks to preserve",
            }

        # Simple similarity check (in production would be more sophisticated)
        similarity_score = random.random()  # Placeholder

        if similarity_score > 0.7:
            return {
                "approach": "fine_tune",  # Similar task, can fine-tune
                "rationale": f"High similarity to existing tasks",
                "ewc_lambda": self.ewc.lambda_ewc
                / 2,  # Lower penalty for similar tasks
            }
        else:
            return {
                "approach": "ewc_protected",  # Different task, use EWC
                "rationale": "Different task domain, protect previous knowledge",
                "ewc_lambda": self.ewc.lambda_ewc,
            }

    def get_status(self) -> Dict:
        """Get overall learning status"""
        return {
            "tasks_trained": self.ewc.task_count,
            "patterns_learned": len(self.online.patterns),
            "feedback_received": len(self.online.feedback_history),
            "ewc_status": self.ewc.get_ewc_loss({}),
            "online_stats": self.online.get_learning_stats(),
        }


def demo():
    """Demo continual learning"""
    print("=" * 50)
    print("SOV3 Continual Learning Demo")
    print("=" * 50)

    learning = ContinualLearningManager()

    # Train on first task
    print("\n1. Training on task: customer_support")
    examples = [
        TaskExample({"query": "help"}, {"response": "assist"}, "customer_support"),
        TaskExample({"query": "question"}, {"response": "answer"}, "customer_support"),
        TaskExample({"query": "issue"}, {"response": "resolve"}, "customer_support"),
    ]
    params = {"weights": [0.5, 0.3, 0.2], "bias": 0.1}
    result = learning.train_on_task("customer_support", examples, params)
    print(f"   Result: {result}")

    # Train on second task
    print("\n2. Training on task: code_generation")
    examples2 = [
        TaskExample({"query": "function"}, {"response": "def"}, "code_generation"),
        TaskExample({"query": "class"}, {"response": "class"}, "code_generation"),
    ]
    result2 = learning.train_on_task("code_generation", examples2, params.copy())
    print(f"   Result: {result2}")

    # Learn from interaction
    print("\n3. Learning from interactions...")
    learning.learn_from_interaction(
        {"prediction": "help", "context": {"query": "help me"}},
        {"result": "helping", "correct": True},
    )
    learning.learn_from_interaction(
        {"prediction": "answer", "context": {"query": "what is"}},
        {"result": "answering", "correct": True},
    )
    learning.learn_from_interaction(
        {"prediction": "resolve", "context": {"query": "fix bug"}},
        {"result": "debug", "correct": False},
    )

    # Get recommendations
    print("\n4. Training recommendations:")
    rec = learning.get_training_recommendation("new_task")
    print(f"   Approach: {rec['approach']}")
    print(f"   Rationale: {rec['rationale']}")

    # Status
    print("\n5. Learning status:")
    status = learning.get_status()
    print(f"   Tasks trained: {status['tasks_trained']}")
    print(f"   Feedback count: {status['feedback_received']}")
    print(f"   Online stats: {status['online_stats']}")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print("Usage: python sov3_continual_learning.py demo")
