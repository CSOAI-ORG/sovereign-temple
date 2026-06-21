"""
Relationship Evolution Predictor Neural Network
Forecasts trust trajectory and relationship dynamics over time
Architecture: Input -> 128 -> 64 -> 32 -> 3 outputs
"""

import numpy as np
from sklearn.neural_network import MLPRegressor
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from . import base_model


class RelationshipEvolutionNN(base_model.BaseNeuralModel):
    """
    Predicts how relationships will evolve over time
    Outputs: future_trust_score, relationship_trajectory, engagement_prediction
    """
    
    def __init__(self, model_dir: str = "models"):
        super().__init__("relationship_evolution_nn", model_dir)
        self.feature_names = [
            "current_trust",
            "interaction_frequency",
            "care_score_avg",
            "conflict_count",
            "collaboration_count",
            "days_since_first_contact",
            "reciprocity_score",
            "vulnerability_sharing",
            "boundary_respect",
            "shared_value_alignment"
        ]
    
    def extract_features(self, relationship_data: Dict[str, Any]) -> np.ndarray:
        """Extract features from relationship data"""
        features = [
            relationship_data.get("current_trust", 0.5),
            relationship_data.get("interaction_frequency", 0),  # per week
            relationship_data.get("care_score_avg", 0.5),
            relationship_data.get("conflict_count", 0),
            relationship_data.get("collaboration_count", 0),
            relationship_data.get("days_since_first_contact", 0) / 365.0,  # normalized to years
            relationship_data.get("reciprocity_score", 0.5),
            relationship_data.get("vulnerability_sharing", 0.5),
            relationship_data.get("boundary_respect", 0.5),
            relationship_data.get("shared_value_alignment", 0.5)
        ]
        return np.array(features)
    
    def _generate_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic relationship evolution data"""
        
        np.random.seed(42)
        n_samples = 500
        
        # Generate feature combinations
        current_trust = np.random.uniform(0.1, 1.0, n_samples)
        interaction_freq = np.random.uniform(0, 20, n_samples)  # interactions per week
        care_score = np.random.uniform(0.2, 1.0, n_samples)
        conflicts = np.random.poisson(2, n_samples)
        collaborations = np.random.poisson(5, n_samples)
        relationship_age = np.random.uniform(0, 3, n_samples)  # years
        reciprocity = np.random.uniform(0.3, 1.0, n_samples)
        vulnerability = np.random.uniform(0.1, 0.9, n_samples)
        boundary_respect = np.random.uniform(0.4, 1.0, n_samples)
        value_alignment = np.random.uniform(0.2, 1.0, n_samples)
        
        X = np.column_stack([
            current_trust, interaction_freq, care_score, conflicts,
            collaborations, relationship_age, reciprocity, vulnerability,
            boundary_respect, value_alignment
        ])
        
        # Generate labels based on relationship dynamics
        # Future trust (6 months ahead) depends on current state and trends
        trust_change = (
            (care_score - 0.5) * 0.3 +  # Care drives trust
            (reciprocity - 0.5) * 0.2 +  # Reciprocity helps
            (boundary_respect - 0.5) * 0.15 +  # Boundaries matter
            (value_alignment - 0.5) * 0.2 +  # Shared values
            (collaborations / 10) * 0.1 +  # Collaboration builds trust
            -(conflicts / 5) * 0.1 +  # Conflicts reduce trust
            np.random.normal(0, 0.05, n_samples)  # noise
        )
        
        future_trust = np.clip(current_trust + trust_change, 0.1, 1.0)
        
        # Trajectory: -1 (declining) to 1 (growing)
        trajectory = np.clip(trust_change * 3, -1, 1)
        
        # Engagement prediction (0-1) - likelihood of continued engagement
        engagement = (
            current_trust * 0.3 +
            care_score * 0.25 +
            reciprocity * 0.2 +
            np.clip(interaction_freq / 20, 0, 1) * 0.15 +
            (1 - np.clip(conflicts / 5, 0, 1)) * 0.1 +
            np.random.normal(0, 0.05, n_samples)
        )
        engagement = np.clip(engagement, 0, 1)
        
        y = np.column_stack([future_trust, trajectory, engagement])
        
        return X, y
    
    def train_model(self, training_data: Optional[Any] = None) -> Dict[str, float]:
        """Train the relationship evolution model"""
        
        X, y = self._generate_training_data()
        
        # Data augmentation from continual learning pipeline
        if training_data:
            new_count = len([t for t in training_data if isinstance(t, str) and len(t.strip()) > 10])
            if new_count and len(X) > 0:
                np.random.seed(42 + new_count)
                aug_X = X + np.random.normal(0, 0.02, X.shape)
                aug_y = np.clip(y + np.random.normal(0, 0.02, y.shape), -1, 1)
                n_aug = min(new_count, len(X) * 2)
                indices = np.random.choice(len(X), size=n_aug, replace=True)
                X = np.vstack([X, aug_X[indices]])
                y = np.vstack([y, aug_y[indices]])
        
        # Create and train MLP
        self.model = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
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
        output_names = ["future_trust", "trajectory", "engagement"]
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
    
    def predict(self, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
        """Predict relationship evolution"""
        if not self.is_trained or self.model is None:
            return {"error": "Model not trained", "predicted_trust_6mo": 0.5, "trajectory": {"value": 0.0, "description": "unknown"}}

        features = self.safe_features(self.extract_features(relationship_data)).reshape(1, -1)
        prediction = self.model.predict(features)[0]
        
        future_trust = float(prediction[0])
        trajectory = float(prediction[1])
        engagement = float(prediction[2])
        
        # Interpret trajectory
        if trajectory > 0.3:
            trajectory_desc = "rapidly_strengthening"
        elif trajectory > 0.1:
            trajectory_desc = "gradually_improving"
        elif trajectory > -0.1:
            trajectory_desc = "stable"
        elif trajectory > -0.3:
            trajectory_desc = "gradually_declining"
        else:
            trajectory_desc = "at_risk"
        
        # Risk assessment
        risk_factors = []
        if relationship_data.get("conflict_count", 0) > 3:
            risk_factors.append("frequent_conflicts")
        if relationship_data.get("reciprocity_score", 0.5) < 0.4:
            risk_factors.append("low_reciprocity")
        if relationship_data.get("care_score_avg", 0.5) < 0.5:
            risk_factors.append("care_deficit")
        if future_trust < 0.4:
            risk_factors.append("low_predicted_trust")
        
        # Recommendations
        recommendations = []
        if trajectory < 0:
            recommendations.append("Increase care-centered interactions")
        if relationship_data.get("reciprocity_score", 0.5) < 0.5:
            recommendations.append("Focus on mutual value exchange")
        if relationship_data.get("conflict_count", 0) > 2:
            recommendations.append("Address underlying conflicts through dialogue")
        if engagement < 0.5:
            recommendations.append("Find ways to increase meaningful engagement")
        
        return {
            "current_trust": relationship_data.get("current_trust", 0.5),
            "predicted_trust_6mo": round(future_trust, 3),
            "trust_change": round(future_trust - relationship_data.get("current_trust", 0.5), 3),
            "trajectory": {
                "value": round(trajectory, 3),
                "description": trajectory_desc
            },
            "engagement_likelihood": round(engagement, 3),
            "relationship_health": self._health_score(future_trust, trajectory, engagement),
            "risk_factors": risk_factors,
            "recommendations": recommendations if recommendations else ["Continue current positive trajectory"]
        }
    
    def _health_score(self, trust: float, trajectory: float, engagement: float) -> str:
        """Calculate overall relationship health"""
        score = trust * 0.4 + (trajectory + 1) / 2 * 0.3 + engagement * 0.3
        
        if score >= 0.8:
            return "thriving"
        elif score >= 0.6:
            return "healthy"
        elif score >= 0.4:
            return "stable"
        elif score >= 0.2:
            return "needs_attention"
        else:
            return "at_risk"


if __name__ == "__main__":
    model = RelationshipEvolutionNN(model_dir="../models")
    metrics = model.train_model()
    print(f"Training metrics: {metrics}")
    
    # Test predictions
    test_relationships = [
        {
            "current_trust": 0.8,
            "interaction_frequency": 10,
            "care_score_avg": 0.9,
            "conflict_count": 0,
            "collaboration_count": 5,
            "days_since_first_contact": 180,
            "reciprocity_score": 0.85,
            "vulnerability_sharing": 0.8,
            "boundary_respect": 0.9,
            "shared_value_alignment": 0.9
        },
        {
            "current_trust": 0.4,
            "interaction_frequency": 2,
            "care_score_avg": 0.3,
            "conflict_count": 4,
            "collaboration_count": 1,
            "days_since_first_contact": 30,
            "reciprocity_score": 0.3,
            "vulnerability_sharing": 0.2,
            "boundary_respect": 0.4,
            "shared_value_alignment": 0.3
        }
    ]
    
    for rel in test_relationships:
        result = model.predict(rel)
        print(f"\nRelationship: trust={rel['current_trust']}")
        print(f"Prediction: {result['predicted_trust_6mo']}, {result['trajectory']['description']}")
        print(f"Health: {result['relationship_health']}")
