"""
Stochastic Resonance Engine — learnable noise injection for creativity.

Stochastic resonance is the phenomenon where adding noise to a nonlinear
system actually IMPROVES signal detection. In biological neural networks,
moderate noise enhances weak signal transmission (Collins et al., 1995).

For Sovereign's creativity engine:
- Weak signals = faint cross-domain associations, low-confidence creative ideas
- Noise = controlled random perturbation of feature vectors
- Resonance = optimal noise level where creativity assessment improves

The engine auto-tunes noise amplitude based on output quality feedback,
finding the "sweet spot" where noise amplifies genuine creative connections
without drowning them in randomness.

Dependencies: numpy only (no new pip installs)
"""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


class StochasticResonanceEngine:
    """Applies optimal noise injection to creativity feature vectors.

    Algorithm:
    1. Start with moderate noise amplitude (σ = 0.15)
    2. For each creativity assessment:
       a. Generate noised variant of input features
       b. Compare creativity score with/without noise
       c. If noised version scores higher → increase σ slightly
       d. If noised version scores lower → decrease σ slightly
    3. Over time, σ converges to the optimal resonance amplitude.

    The engine maintains separate noise profiles per feature, allowing
    different optimal noise levels for different input dimensions.
    """

    def __init__(
        self,
        n_features: int = 12,
        initial_sigma: float = 0.15,
        learning_rate: float = 0.02,
        min_sigma: float = 0.01,
        max_sigma: float = 0.5,
        momentum: float = 0.9,
    ):
        self.n_features = n_features
        self.sigma = np.full(n_features, initial_sigma)
        self.learning_rate = learning_rate
        self.min_sigma = min_sigma
        self.max_sigma = max_sigma
        self.momentum = momentum

        # Velocity for momentum-based updates
        self.velocity = np.zeros(n_features)

        # History for analysis
        self.history: List[Dict[str, Any]] = []
        self.improvement_count = 0
        self.total_applications = 0

        # Feature-specific noise profiles (some features benefit more from noise)
        # Based on creativity theory: novelty_score, surprise_factor, cross_domain_links
        # benefit most from noise; care_alignment, coherence_score should stay stable
        self.noise_sensitivity = np.array([
            1.2,   # novelty_score — high noise benefit
            1.3,   # domain_distance — high noise benefit (explore far)
            0.7,   # emotional_valence — moderate stability
            1.1,   # curiosity_level — noise helps exploration
            0.9,   # aesthetics_level — moderate stability
            1.0,   # association_count — neutral
            0.4,   # care_alignment — LOW noise (care must stay stable)
            0.5,   # coherence_score — LOW noise (coherence is signal)
            1.4,   # surprise_factor — HIGHEST noise benefit
            0.8,   # tradition_count — moderate
            1.2,   # cross_domain_links — high noise benefit
            0.6,   # dream_phase_origin — low noise
        ])

        # Trim or pad to match n_features
        if len(self.noise_sensitivity) < n_features:
            self.noise_sensitivity = np.pad(
                self.noise_sensitivity,
                (0, n_features - len(self.noise_sensitivity)),
                constant_values=1.0,
            )
        elif len(self.noise_sensitivity) > n_features:
            self.noise_sensitivity = self.noise_sensitivity[:n_features]

    def inject_noise(
        self,
        features: np.ndarray,
        temperature: float = 1.0,
    ) -> np.ndarray:
        """Inject stochastic resonance noise into a feature vector.

        Args:
            features: Input feature vector of shape (n_features,).
            temperature: Noise scaling factor (>1 = more noise, <1 = less).

        Returns:
            Noised feature vector with same shape.
        """
        # Generate Gaussian noise scaled by per-feature sigma and sensitivity
        effective_sigma = self.sigma * self.noise_sensitivity * temperature
        noise = np.random.normal(0, effective_sigma)

        noised = features + noise

        # Soft clamp — features generally in [-1, 1] or [0, 1]
        # Don't hard-clamp, let the creativity model handle out-of-range
        return noised

    def inject_noise_batch(
        self,
        features: np.ndarray,
        n_variants: int = 5,
        temperature: float = 1.0,
    ) -> np.ndarray:
        """Generate multiple noised variants of a feature vector.

        Args:
            features: Input feature vector of shape (n_features,).
            n_variants: Number of noised variants to generate.
            temperature: Noise scaling factor.

        Returns:
            Array of shape (n_variants, n_features).
        """
        variants = []
        for _ in range(n_variants):
            variants.append(self.inject_noise(features, temperature))
        return np.array(variants)

    def update_from_feedback(
        self,
        original_score: float,
        noised_score: float,
        feature_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update noise parameters based on creativity score feedback.

        If noised version scored higher → noise was helpful → increase σ.
        If noised version scored lower → noise was harmful → decrease σ.

        Args:
            original_score: Creativity score without noise.
            noised_score: Creativity score with noise.
            feature_index: If provided, only update this feature's sigma.

        Returns:
            Update summary dict.
        """
        self.total_applications += 1
        improvement = noised_score - original_score

        # Gradient direction: positive improvement → increase noise
        gradient = np.sign(improvement) * self.learning_rate

        if feature_index is not None:
            # Update single feature
            self.velocity[feature_index] = (
                self.momentum * self.velocity[feature_index] + gradient
            )
            self.sigma[feature_index] += self.velocity[feature_index]
        else:
            # Update all features (scaled by sensitivity)
            self.velocity = self.momentum * self.velocity + gradient * self.noise_sensitivity
            self.sigma += self.velocity

        # Clamp sigma
        self.sigma = np.clip(self.sigma, self.min_sigma, self.max_sigma)

        if improvement > 0:
            self.improvement_count += 1

        record = {
            "original_score": round(original_score, 4),
            "noised_score": round(noised_score, 4),
            "improvement": round(improvement, 4),
            "mean_sigma": round(float(np.mean(self.sigma)), 4),
            "timestamp": datetime.now().isoformat(),
        }
        self.history.append(record)

        # Keep history bounded
        if len(self.history) > 500:
            self.history = self.history[-250:]

        return record

    def get_optimal_temperature(self) -> float:
        """Compute optimal noise temperature from recent feedback history.

        Analyzes the last N feedback records to find the temperature
        that maximizes creativity improvement.

        Returns:
            Recommended temperature multiplier.
        """
        if len(self.history) < 5:
            return 1.0  # Default until enough data

        recent = self.history[-50:]
        improvements = [r["improvement"] for r in recent]

        mean_improvement = np.mean(improvements)
        std_improvement = np.std(improvements) if len(improvements) > 1 else 0.1

        # If improvements are consistently positive → can be more aggressive
        if mean_improvement > 0.02:
            return min(1.5, 1.0 + mean_improvement * 2)
        # If improvements are consistently negative → reduce noise
        elif mean_improvement < -0.02:
            return max(0.5, 1.0 + mean_improvement * 2)
        # Sweet spot — maintain
        else:
            return 1.0

    def get_resonance_profile(self) -> Dict[str, Any]:
        """Get the current noise resonance profile per feature.

        Returns:
            Dict with per-feature sigma values and metadata.
        """
        from .creativity_nn import FEATURE_NAMES

        feature_names = FEATURE_NAMES if len(FEATURE_NAMES) == self.n_features else [
            f"feature_{i}" for i in range(self.n_features)
        ]

        profile = {}
        for i, name in enumerate(feature_names):
            profile[name] = {
                "sigma": round(float(self.sigma[i]), 4),
                "sensitivity": round(float(self.noise_sensitivity[i]), 4),
                "effective_sigma": round(float(self.sigma[i] * self.noise_sensitivity[i]), 4),
            }

        return {
            "profile": profile,
            "mean_sigma": round(float(np.mean(self.sigma)), 4),
            "optimal_temperature": self.get_optimal_temperature(),
            "total_applications": self.total_applications,
            "improvement_rate": round(
                self.improvement_count / max(1, self.total_applications), 4
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "n_features": self.n_features,
            "mean_sigma": round(float(np.mean(self.sigma)), 4),
            "max_sigma": round(float(np.max(self.sigma)), 4),
            "min_sigma": round(float(np.min(self.sigma)), 4),
            "total_applications": self.total_applications,
            "improvement_count": self.improvement_count,
            "improvement_rate": round(
                self.improvement_count / max(1, self.total_applications), 4
            ),
            "optimal_temperature": self.get_optimal_temperature(),
            "recent_history": self.history[-5:] if self.history else [],
        }


def apply_stochastic_resonance(
    features: Dict[str, float],
    engine: Optional[StochasticResonanceEngine] = None,
    temperature: float = 1.0,
) -> Dict[str, float]:
    """Convenience function: apply stochastic resonance to a feature dict.

    Args:
        features: Named feature dict (matching FEATURE_NAMES).
        engine: StochasticResonanceEngine instance (creates default if None).
        temperature: Noise scaling factor.

    Returns:
        Noised feature dict.
    """
    from .creativity_nn import FEATURE_NAMES

    if engine is None:
        engine = StochasticResonanceEngine()

    # Convert dict to array
    arr = np.zeros(len(FEATURE_NAMES))
    for i, name in enumerate(FEATURE_NAMES):
        arr[i] = float(features.get(name, 0.0))

    # Inject noise
    noised = engine.inject_noise(arr, temperature)

    # Convert back to dict
    result = {}
    for i, name in enumerate(FEATURE_NAMES):
        result[name] = round(float(noised[i]), 4)

    return result
