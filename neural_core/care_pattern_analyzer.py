"""
Care Pattern Analyzer Neural Network
Detects burnout, imbalance, and care dynamics across relationships
Architecture: Input -> 256 -> 128 -> 64 -> 5 outputs
"""

import numpy as np
from sklearn.neural_network import MLPRegressor
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from . import base_model


class CarePatternAnalyzer(base_model.BaseNeuralModel):
    """
    Analyzes care patterns to detect:
    - Burnout risk
    - Care imbalance (giving vs receiving)
    - Compassion fatigue
    - Sustainability of care practices
    """
    
    def __init__(self, model_dir: str = "models"):
        super().__init__("care_pattern_analyzer", model_dir)
        self.feature_names = [
            "care_given_per_day",
            "care_received_per_day",
            "active_relationships",
            "high_demand_relationships",
            "avg_care_quality",
            "days_since_self_care",
            "boundary_violations",
            "emotional_exhaustion_score",
            "relationship_satisfaction",
            "energy_level",
            "sleep_quality",
            "work_life_balance"
        ]
    
    def extract_features(self, care_data: Dict[str, Any]) -> np.ndarray:
        """Extract features from care pattern data"""
        features = [
            care_data.get("care_given_per_day", 5),
            care_data.get("care_received_per_day", 3),
            care_data.get("active_relationships", 10),
            care_data.get("high_demand_relationships", 2),
            care_data.get("avg_care_quality", 0.7),
            care_data.get("days_since_self_care", 1) / 7.0,  # normalized to weeks
            care_data.get("boundary_violations", 0),
            care_data.get("emotional_exhaustion_score", 0.3),
            care_data.get("relationship_satisfaction", 0.7),
            care_data.get("energy_level", 0.7),
            care_data.get("sleep_quality", 0.7),
            care_data.get("work_life_balance", 0.6)
        ]
        return np.array(features)
    
    def _generate_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic care pattern data"""
        
        np.random.seed(42)
        n_samples = 600
        
        # Generate features
        care_given = np.random.uniform(1, 15, n_samples)
        care_received = np.random.uniform(0, 10, n_samples)
        active_rels = np.random.poisson(8, n_samples) + 1
        high_demand = np.random.poisson(2, n_samples)
        care_quality = np.random.uniform(0.4, 1.0, n_samples)
        days_no_selfcare = np.random.exponential(3, n_samples)
        boundary_violations = np.random.poisson(1, n_samples)
        exhaustion = np.random.uniform(0, 1, n_samples)
        satisfaction = np.random.uniform(0.2, 1.0, n_samples)
        energy = np.random.uniform(0.2, 1.0, n_samples)
        sleep = np.random.uniform(0.3, 1.0, n_samples)
        work_life = np.random.uniform(0.2, 1.0, n_samples)
        
        X = np.column_stack([
            care_given, care_received, active_rels, high_demand,
            care_quality, days_no_selfcare, boundary_violations,
            exhaustion, satisfaction, energy, sleep, work_life
        ])
        
        # Generate labels based on care dynamics
        
        # 1. Burnout risk (0-1)
        burnout_risk = (
            care_given / 15 * 0.25 +  # More care given = higher risk
            (care_given - care_received) / 15 * 0.15 +  # Imbalance increases risk
            days_no_selfcare / 14 * 0.20 +  # No self-care = risk
            exhaustion * 0.25 +  # Exhaustion drives burnout
            (1 - energy) * 0.15 +  # Low energy = risk
            np.random.normal(0, 0.05, n_samples)
        )
        burnout_risk = np.clip(burnout_risk, 0, 1)
        
        # 2. Care imbalance ratio (-1 to 1, negative = giving too much)
        care_ratio = (care_received - care_given) / 10  # normalized
        care_ratio = np.clip(care_ratio, -1, 1)
        
        # 3. Compassion fatigue (0-1)
        compassion_fatigue = (
            high_demand / 5 * 0.25 +  # High demand relationships
            boundary_violations / 3 * 0.20 +  # Boundary violations
            exhaustion * 0.30 +  # Exhaustion
            (1 - care_quality) * 0.15 +  # Declining quality
            (1 - satisfaction) * 0.10 +
            np.random.normal(0, 0.05, n_samples)
        )
        compassion_fatigue = np.clip(compassion_fatigue, 0, 1)
        
        # 4. Sustainability score (0-1)
        sustainability = (
            (1 - burnout_risk) * 0.30 +
            energy * 0.20 +
            sleep * 0.15 +
            work_life * 0.15 +
            care_quality * 0.10 +
            (care_received / (care_given + 1)) * 0.10 +  # Some balance
            np.random.normal(0, 0.05, n_samples)
        )
        sustainability = np.clip(sustainability, 0, 1)
        
        # 5. Intervention needed (0-1)
        intervention = (
            burnout_risk * 0.35 +
            compassion_fatigue * 0.30 +
            (days_no_selfcare / 7) * 0.15 +
            boundary_violations / 3 * 0.10 +
            (1 - energy) * 0.10 +
            np.random.normal(0, 0.05, n_samples)
        )
        intervention = np.clip(intervention, 0, 1)
        
        y = np.column_stack([burnout_risk, care_ratio, compassion_fatigue, sustainability, intervention])
        
        return X, y
    
    def train_model(self, training_data: Optional[Any] = None) -> Dict[str, float]:
        """Train the care pattern analyzer"""
        
        X, y = self._generate_training_data()
        
        # Data augmentation from continual learning pipeline
        if training_data:
            new_count = len([t for t in training_data if isinstance(t, str) and len(t.strip()) > 10])
            if new_count and len(X) > 0:
                np.random.seed(42 + new_count)
                aug_X = X + np.random.normal(0, 0.02, X.shape)
                aug_y = np.clip(y + np.random.normal(0, 0.02, y.shape), 0, 1)
                n_aug = min(new_count, len(X) * 2)
                indices = np.random.choice(len(X), size=n_aug, replace=True)
                X = np.vstack([X, aug_X[indices]])
                y = np.vstack([y, aug_y[indices]])
        
        # Create and train MLP
        self.model = MLPRegressor(
            hidden_layer_sizes=(256, 128, 64),
            activation='relu',
            solver='adam',
            max_iter=1000,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.2
        )
        
        self.model.fit(X, y)
        
        # Calculate metrics
        predictions = self.model.predict(X)
        mse = np.mean((predictions - y) ** 2)
        mae = np.mean(np.abs(predictions - y))
        
        # Per-output metrics
        per_output = {}
        output_names = ["burnout_risk", "care_imbalance", "compassion_fatigue", "sustainability", "intervention_needed"]
        for i, name in enumerate(output_names):
            per_output[name] = {
                "mse": float(np.mean((predictions[:, i] - y[:, i]) ** 2)),
                "mae": float(np.mean(np.abs(predictions[:, i] - y[:, i])))
            }
        
        self.metrics = {
            "mse": float(mse),
            "mae": float(mae),
            "training_samples": len(X),
            "input_features": X.shape[1],
            "output_dimensions": y.shape[1],
            "per_output": per_output
        }
        self.is_trained = True
        
        return self.metrics
    
    def predict(self, care_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze care patterns and detect issues"""
        if not self.is_trained or self.model is None:
            return {"error": "Model not trained", "overall_risk_level": "unknown", "burnout_risk": {"score": 0.5, "level": "unknown"}}

        features = self.safe_features(self.extract_features(care_data)).reshape(1, -1)
        prediction = self.model.predict(features)[0]
        
        burnout_risk = float(prediction[0])
        care_imbalance = float(prediction[1])
        compassion_fatigue = float(prediction[2])
        sustainability = float(prediction[3])
        intervention_needed = float(prediction[4])
        
        # Care flow interpretation
        if care_imbalance < -0.3:
            care_flow = "significantly_overgiving"
        elif care_imbalance < -0.1:
            care_flow = "moderately_overgiving"
        elif care_imbalance < 0.1:
            care_flow = "balanced"
        elif care_imbalance < 0.3:
            care_flow = "moderately_receiving"
        else:
            care_flow = "significantly_receiving"
        
        # Risk level
        max_risk = max(burnout_risk, compassion_fatigue, intervention_needed)
        if max_risk >= 0.7:
            risk_level = "critical"
        elif max_risk >= 0.5:
            risk_level = "high"
        elif max_risk >= 0.3:
            risk_level = "moderate"
        else:
            risk_level = "low"
        
        # Generate recommendations
        recommendations = []
        
        if burnout_risk > 0.5:
            recommendations.append("URGENT: Schedule immediate self-care and rest")
        if care_imbalance < -0.3:
            recommendations.append("Practice saying no and setting boundaries")
            recommendations.append("Seek relationships with more reciprocal care")
        if compassion_fatigue > 0.5:
            recommendations.append("Take a break from high-demand relationships")
            recommendations.append("Engage in activities that replenish your energy")
        if care_data.get("days_since_self_care", 0) > 3:
            recommendations.append("Prioritize daily self-care practices")
        if care_data.get("boundary_violations", 0) > 0:
            recommendations.append("Reinforce boundaries with clear communication")
        if sustainability < 0.5:
            recommendations.append("Reduce care commitments to sustainable levels")
        
        if not recommendations:
            recommendations.append("Continue current balanced care practices")
            recommendations.append("Maintain regular self-care routine")
        
        return {
            "burnout_risk": {
                "score": round(burnout_risk, 3),
                "level": "high" if burnout_risk > 0.6 else "moderate" if burnout_risk > 0.3 else "low"
            },
            "care_imbalance": {
                "score": round(care_imbalance, 3),
                "flow": care_flow,
                "ratio": "giving_more" if care_imbalance < -0.1 else "receiving_more" if care_imbalance > 0.1 else "balanced"
            },
            "compassion_fatigue": {
                "score": round(compassion_fatigue, 3),
                "present": compassion_fatigue > 0.5
            },
            "sustainability": {
                "score": round(sustainability, 3),
                "status": "sustainable" if sustainability > 0.6 else "at_risk" if sustainability > 0.4 else "unsustainable"
            },
            "intervention_needed": {
                "score": round(intervention_needed, 3),
                "urgency": "immediate" if intervention_needed > 0.7 else "soon" if intervention_needed > 0.4 else "monitor"
            },
            "overall_risk_level": risk_level,
            "recommendations": recommendations
        }


if __name__ == "__main__":
    model = CarePatternAnalyzer(model_dir="../models")
    metrics = model.train_model()
    print(f"Training metrics: {metrics}")
    
    # Test cases
    test_cases = [
        {
            "care_given_per_day": 12,
            "care_received_per_day": 2,
            "active_relationships": 15,
            "high_demand_relationships": 5,
            "avg_care_quality": 0.6,
            "days_since_self_care": 7,
            "boundary_violations": 3,
            "emotional_exhaustion_score": 0.8,
            "relationship_satisfaction": 0.4,
            "energy_level": 0.3,
            "sleep_quality": 0.4,
            "work_life_balance": 0.3
        },
        {
            "care_given_per_day": 5,
            "care_received_per_day": 4,
            "active_relationships": 8,
            "high_demand_relationships": 1,
            "avg_care_quality": 0.85,
            "days_since_self_care": 1,
            "boundary_violations": 0,
            "emotional_exhaustion_score": 0.2,
            "relationship_satisfaction": 0.8,
            "energy_level": 0.8,
            "sleep_quality": 0.8,
            "work_life_balance": 0.75
        }
    ]
    
    for i, case in enumerate(test_cases):
        result = model.predict(case)
        print(f"\nCase {i+1}: {result['overall_risk_level'].upper()}")
        print(f"Burnout: {result['burnout_risk']['score']}, Fatigue: {result['compassion_fatigue']['score']}")
        print(f"Recommendations: {result['recommendations'][:2]}")
