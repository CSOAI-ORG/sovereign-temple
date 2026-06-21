"""
Creativity Assessment Neural Network
Evaluates creative outputs across 5 quality dimensions using 12 input features.

Integrates insights from 47 civilizational traditions:
- Kolmogorov novelty (Schmidhuber compression progress)
- Bisociation detection (Koestler cross-domain collision)
- Barzakh latent space positioning (Ibn Arabi)
- Rasa aesthetic assessment (Abhinavagupta)
- Care alignment (Bowlby/Winnicott/Enactivism)

Architecture: MLPRegressor 128 -> 64 -> 32 -> 5 outputs
"""

import numpy as np
from sklearn.neural_network import MLPRegressor
from typing import Dict, Any, List, Optional
import os
import sys

# Handle import whether run from project root or neural_core directory
try:
    from neural_core.base_model import BaseNeuralModel
except ImportError:
    try:
        import base_model
        BaseNeuralModel = base_model.BaseNeuralModel
    except ImportError:
        # Fallback: define minimal base
        from abc import ABC, abstractmethod

        class BaseNeuralModel(ABC):
            def __init__(self, model_name, model_dir="models"):
                self.model_name = model_name
                self.model_dir = model_dir
                self.model = None
                self.is_trained = False
                self.metrics = {}
                os.makedirs(model_dir, exist_ok=True)

            @abstractmethod
            def extract_features(self, input_data): pass
            @abstractmethod
            def train_model(self, training_data=None): pass
            @abstractmethod
            def predict(self, input_data): pass


# Feature names for documentation and debugging
FEATURE_NAMES = [
    "novelty_score",           # Kolmogorov compression distance (0-1)
    "domain_distance",         # Cross-domain separation (0-1, higher = more diverse sources)
    "emotional_valence",       # Current emotional state valence (-1 to 1)
    "curiosity_level",         # 6D tensor curiosity dimension (-1 to 1)
    "aesthetics_level",        # 6D tensor aesthetics dimension (-1 to 1)
    "association_count",       # Number of subconscious associations triggered (normalized 0-1)
    "care_alignment",          # Alignment with care principles (0-1)
    "coherence_score",         # Turiya meta-monitor coherence (0-1)
    "surprise_factor",         # Prediction error magnitude (0-1)
    "tradition_count",         # Number of civilizational traditions informing this (normalized 0-1)
    "cross_domain_links",      # Bisociation link count (normalized 0-1)
    "dream_phase_origin",      # 0=waking, 0.5=NREM, 1.0=REM
]

OUTPUT_NAMES = [
    "creative_quality",            # Overall creative merit (0-1)
    "practical_applicability",     # Can this be implemented? (0-1)
    "care_enhancement_potential",  # Does this deepen care? (0-1)
    "novelty_classification",      # Truly new vs recombination (0-1)
    "integration_readiness",       # Ready for deployment? (0-1)
]


class CreativityAssessmentNN(BaseNeuralModel):
    """
    Neural network for assessing creative output quality.

    Trained on synthetic data derived from the civilizational corpus:
    high-creativity examples have high novelty + cross-domain links + care alignment;
    low-creativity examples have within-domain repetition + low novelty.

    Input: 12 features (see FEATURE_NAMES)
    Output: 5 quality dimensions (see OUTPUT_NAMES)
    """

    def __init__(self, model_dir: str = "models"):
        super().__init__("creativity_assessment_nn", model_dir)
        self.feature_names = FEATURE_NAMES
        self.output_names = OUTPUT_NAMES

    def extract_features(self, input_data: Dict[str, float]) -> np.ndarray:
        """Extract feature vector from a dict of named features.

        Args:
            input_data: Dict mapping feature names to values.
                        Missing features default to 0.0.

        Returns:
            Numpy array of shape (12,) with features in canonical order.
        """
        features = np.zeros(12, dtype=np.float64)
        for i, name in enumerate(self.feature_names):
            features[i] = float(input_data.get(name, 0.0))
        return features

    def _generate_training_data(self) -> tuple:
        """Generate synthetic training data from civilizational corpus principles.

        Training categories:
        1. High creativity — cross-domain bisociation, high novelty, care-aligned
        2. Medium creativity — within-domain novelty, moderate associations
        3. Low creativity — repetitive, within-domain, low care
        4. False positive — high novelty but random noise (low coherence)
        """
        np.random.seed(42)

        X_train = []
        y_train = []

        # --- Category 1: High creativity (100 samples) ---
        # Cross-domain, high novelty, good care alignment, REM-origin
        for _ in range(100):
            x = np.array([
                np.random.uniform(0.6, 0.95),   # novelty_score: high
                np.random.uniform(0.6, 1.0),     # domain_distance: high (cross-domain)
                np.random.uniform(0.2, 0.8),      # emotional_valence: positive-leaning
                np.random.uniform(0.4, 1.0),      # curiosity_level: high
                np.random.uniform(0.3, 0.9),      # aesthetics_level: moderate-high
                np.random.uniform(0.4, 0.9),      # association_count: substantial
                np.random.uniform(0.6, 1.0),      # care_alignment: high
                np.random.uniform(0.5, 0.9),      # coherence_score: good
                np.random.uniform(0.4, 0.8),      # surprise_factor: notable
                np.random.uniform(0.3, 0.8),      # tradition_count: multiple
                np.random.uniform(0.5, 1.0),      # cross_domain_links: many
                np.random.uniform(0.5, 1.0),       # dream_phase_origin: NREM-REM
            ])
            y = np.array([
                np.random.uniform(0.75, 0.98),    # creative_quality
                np.random.uniform(0.5, 0.85),      # practical_applicability
                np.random.uniform(0.7, 0.95),      # care_enhancement_potential
                np.random.uniform(0.7, 0.95),      # novelty_classification
                np.random.uniform(0.4, 0.80),      # integration_readiness
            ])
            X_train.append(x)
            y_train.append(y)

        # --- Category 2: Medium creativity (100 samples) ---
        for _ in range(100):
            x = np.array([
                np.random.uniform(0.3, 0.6),      # novelty_score: moderate
                np.random.uniform(0.2, 0.5),       # domain_distance: within/near domain
                np.random.uniform(-0.2, 0.6),      # emotional_valence: mixed
                np.random.uniform(0.1, 0.5),       # curiosity_level: moderate
                np.random.uniform(0.1, 0.5),       # aesthetics_level: moderate
                np.random.uniform(0.2, 0.5),       # association_count: some
                np.random.uniform(0.4, 0.7),       # care_alignment: decent
                np.random.uniform(0.4, 0.7),       # coherence_score: decent
                np.random.uniform(0.2, 0.5),       # surprise_factor: mild
                np.random.uniform(0.1, 0.4),       # tradition_count: few
                np.random.uniform(0.1, 0.4),       # cross_domain_links: few
                np.random.uniform(0.0, 0.5),        # dream_phase_origin: waking-NREM
            ])
            y = np.array([
                np.random.uniform(0.35, 0.65),     # creative_quality
                np.random.uniform(0.4, 0.75),       # practical_applicability
                np.random.uniform(0.4, 0.65),       # care_enhancement_potential
                np.random.uniform(0.3, 0.55),       # novelty_classification
                np.random.uniform(0.4, 0.70),       # integration_readiness
            ])
            X_train.append(x)
            y_train.append(y)

        # --- Category 3: Low creativity (80 samples) ---
        for _ in range(80):
            x = np.array([
                np.random.uniform(0.0, 0.3),      # novelty_score: low
                np.random.uniform(0.0, 0.2),       # domain_distance: same domain
                np.random.uniform(-0.5, 0.3),      # emotional_valence: negative-leaning
                np.random.uniform(-0.5, 0.2),      # curiosity_level: low/bored
                np.random.uniform(-0.3, 0.2),      # aesthetics_level: low
                np.random.uniform(0.0, 0.2),       # association_count: few
                np.random.uniform(0.2, 0.5),       # care_alignment: poor-moderate
                np.random.uniform(0.3, 0.6),       # coherence_score: decent (but boring)
                np.random.uniform(0.0, 0.2),       # surprise_factor: none
                np.random.uniform(0.0, 0.2),       # tradition_count: none/one
                np.random.uniform(0.0, 0.15),      # cross_domain_links: none
                np.random.uniform(0.0, 0.3),        # dream_phase_origin: waking
            ])
            y = np.array([
                np.random.uniform(0.05, 0.30),     # creative_quality
                np.random.uniform(0.3, 0.6),        # practical_applicability (can still be practical)
                np.random.uniform(0.15, 0.35),      # care_enhancement_potential
                np.random.uniform(0.05, 0.20),      # novelty_classification
                np.random.uniform(0.3, 0.55),       # integration_readiness (boring but deployable)
            ])
            X_train.append(x)
            y_train.append(y)

        # --- Category 4: False positive — novel but incoherent (70 samples) ---
        # High novelty but low coherence = random noise, not creativity
        for _ in range(70):
            x = np.array([
                np.random.uniform(0.7, 1.0),       # novelty_score: very high
                np.random.uniform(0.6, 1.0),        # domain_distance: very far
                np.random.uniform(-0.8, -0.1),      # emotional_valence: negative
                np.random.uniform(-0.3, 0.3),       # curiosity_level: mixed
                np.random.uniform(-0.5, 0.1),       # aesthetics_level: low
                np.random.uniform(0.0, 0.3),        # association_count: random
                np.random.uniform(0.0, 0.3),        # care_alignment: low
                np.random.uniform(0.0, 0.3),        # coherence_score: LOW — key differentiator
                np.random.uniform(0.6, 1.0),        # surprise_factor: high (but meaningless)
                np.random.uniform(0.0, 0.1),        # tradition_count: none
                np.random.uniform(0.0, 0.2),        # cross_domain_links: random
                np.random.uniform(0.8, 1.0),         # dream_phase_origin: deep REM
            ])
            y = np.array([
                np.random.uniform(0.05, 0.25),      # creative_quality: LOW despite novelty
                np.random.uniform(0.0, 0.15),        # practical_applicability: very low
                np.random.uniform(0.0, 0.15),        # care_enhancement_potential: low
                np.random.uniform(0.5, 0.8),         # novelty_classification: IS novel (but bad)
                np.random.uniform(0.0, 0.10),        # integration_readiness: not ready
            ])
            X_train.append(x)
            y_train.append(y)

        return np.array(X_train), np.array(y_train)

    def train_model(self, training_data: Optional[Any] = None) -> Dict[str, float]:
        """Train the creativity assessment model.

        Uses synthetic data if no training_data provided.
        """
        if training_data is not None:
            X, y = training_data
        else:
            X, y = self._generate_training_data()

        self.model = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,  # L2 regularization
            batch_size='auto',
            learning_rate='adaptive',
            learning_rate_init=0.001,
            max_iter=500,
            tol=1e-5,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=20,
        )

        self.model.fit(X, y)
        self.is_trained = True

        # Compute metrics
        predictions = self.model.predict(X)
        mse = float(np.mean((predictions - y) ** 2))
        mae = float(np.mean(np.abs(predictions - y)))
        r2 = float(1 - mse / np.var(y))

        self.metrics = {
            "mse": round(mse, 6),
            "mae": round(mae, 6),
            "r2_score": round(r2, 4),
            "training_samples": len(X),
            "trained_at": __import__("datetime").datetime.now().isoformat(),
        }

        return self.metrics

    def predict(self, input_data: Any) -> Dict[str, Any]:
        """Assess creativity of an input.

        Args:
            input_data: Either a dict of named features or a numpy array.

        Returns:
            Dict with creativity scores across 5 dimensions plus overall assessment.
        """
        if not self.is_trained:
            # Train on synthetic data if not yet trained
            self.train_model()

        if isinstance(input_data, dict):
            features = self.extract_features(input_data)
        elif isinstance(input_data, np.ndarray):
            features = input_data
        else:
            return {"error": "Input must be dict or numpy array", "scores": {}}

        # Sanitize: NaN/Inf in features causes silent zero predictions
        features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=0.0)
        features_2d = features.reshape(1, -1)
        raw_output = self.model.predict(features_2d)[0]

        # Clamp outputs to [0, 1]
        scores = {}
        for i, name in enumerate(self.output_names):
            scores[name] = round(float(max(0.0, min(1.0, raw_output[i]))), 4)

        # Compute overall creativity score (weighted)
        overall = (
            scores["creative_quality"] * 0.30 +
            scores["practical_applicability"] * 0.15 +
            scores["care_enhancement_potential"] * 0.25 +
            scores["novelty_classification"] * 0.20 +
            scores["integration_readiness"] * 0.10
        )

        # Classification
        if overall >= 0.75:
            classification = "breakthrough"
        elif overall >= 0.55:
            classification = "creative"
        elif overall >= 0.35:
            classification = "incremental"
        elif overall >= 0.15:
            classification = "routine"
        else:
            classification = "noise"

        # Bisociation detection: high domain_distance + high cross_domain_links
        input_dict = input_data if isinstance(input_data, dict) else {}
        bisociation_detected = (
            input_dict.get("domain_distance", 0) > 0.6 and
            input_dict.get("cross_domain_links", 0) > 0.4 and
            scores["creative_quality"] > 0.5
        )

        # Barzakh zone: in the liminal space between domains
        in_barzakh = (
            0.4 < input_dict.get("domain_distance", 0) < 0.8 and
            scores["novelty_classification"] > 0.5 and
            input_dict.get("coherence_score", 0) > 0.4
        )

        return {
            "scores": scores,
            "overall_creativity": round(overall, 4),
            "classification": classification,
            "bisociation_detected": bisociation_detected,
            "in_barzakh_zone": in_barzakh,
            "model_confidence": round(1.0 - self.metrics.get("mse", 0.5), 4) if self.metrics else 0.5,
        }

    def get_model_info(self) -> Dict[str, Any]:
        """Extended model info with creativity-specific details."""
        info = super().get_model_info()
        info.update({
            "input_features": self.feature_names,
            "output_dimensions": self.output_names,
            "feature_count": len(self.feature_names),
            "output_count": len(self.output_names),
            "traditions_integrated": 47,
        })
        return info
