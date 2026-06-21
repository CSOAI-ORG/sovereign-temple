"""
Partnership Detection Neural Network
Detects strategic partnership opportunities from text
Architecture: Input -> 128 -> 64 -> 3 outputs (score, urgency, type)
"""

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import Dict, Any, List, Optional
import re
from . import base_model
import pickle
import os


class PartnershipDetectionML(base_model.BaseNeuralModel):
    """
    Neural network for detecting partnership opportunities
    Outputs: opportunity_score (0-1), urgency_level (0-1), partnership_type_vector
    """
    
    def __init__(self, model_dir: str = "models"):
        super().__init__("partnership_detection_ml", model_dir)
        self.vectorizer = TfidfVectorizer(max_features=128, stop_words='english')
        self.svd = None  # TruncatedSVD loaded from retraining pipeline
        self.partnership_types = [
            "strategic",
            "academic", 
            "government",
            "industry",
            "research",
            "funding"
        ]
        
        # Keyword boosters for specific signals
        self.high_value_keywords = {
            "anthropic": 0.3,
            "pentagon": 0.25,
            "dod": 0.25,
            "defense": 0.2,
            "nsf": 0.2,
            "nih": 0.2,
            "grant": 0.15,
            "funding": 0.15,
            "collaboration": 0.15,
            "partnership": 0.15,
            "alliance": 0.15,
            "joint venture": 0.2,
            "strategic": 0.15,
            "investment": 0.15,
            "million": 0.1,
            "billion": 0.2,
        }
    
    def load_model(self) -> bool:
        """Load MLP + vectorizer + SVD from disk."""
        base_ok = super().load_model()
        vec_path = os.path.join(self.model_dir, f"{self.model_name}_vectorizer.pkl")
        svd_path = os.path.join(self.model_dir, f"{self.model_name}_svd.pkl")
        try:
            if os.path.exists(vec_path):
                with open(vec_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
            if os.path.exists(svd_path):
                with open(svd_path, 'rb') as f:
                    self.svd = pickle.load(f)
        except Exception as e:
            print(f"[PartnershipDetectionML] Warning: could not load vectorizer/SVD: {e}")
        return base_ok

    def save_model(self) -> bool:
        """Save MLP + vectorizer + SVD to disk."""
        base_ok = super().save_model()
        vec_path = os.path.join(self.model_dir, f"{self.model_name}_vectorizer.pkl")
        svd_path = os.path.join(self.model_dir, f"{self.model_name}_svd.pkl")
        try:
            if hasattr(self.vectorizer, 'vocabulary_'):
                with open(vec_path, 'wb') as f:
                    pickle.dump(self.vectorizer, f)
            if self.svd is not None:
                with open(svd_path, 'wb') as f:
                    pickle.dump(self.svd, f)
        except Exception as e:
            print(f"[PartnershipDetectionML] Warning: could not save vectorizer/SVD: {e}")
        return base_ok

    def extract_features(self, text: str) -> np.ndarray:
        """Extract TF-IDF features with optional SVD (retraining pipeline) or keyword boost (legacy)."""
        if not hasattr(self.vectorizer, 'vocabulary_'):
            return np.zeros(128)
        
        tfidf_features = self.vectorizer.transform([text]).toarray()[0]
        
        # Apply SVD if available (from retraining pipeline)
        if self.svd is not None:
            return self.svd.transform(tfidf_features.reshape(1, -1))[0]
        
        # Legacy path: keyword boosting (only when no SVD)
        text_lower = text.lower()
        boost = 0.0
        for keyword, weight in self.high_value_keywords.items():
            if keyword in text_lower:
                boost += weight
        
        features = np.concatenate([tfidf_features, [min(boost, 1.0)]])
        return features
    
    def _generate_training_data(self) -> tuple:
        """Generate synthetic training data for partnership detection"""
        
        high_opportunity = [
            "Anthropic is seeking research partners for constitutional AI development with $10M funding",
            "Pentagon announces new defense innovation program for AI cybersecurity partnerships",
            "NSF grant opportunity: $5M available for AI safety research collaborations",
            "Major tech company looking for strategic alliance in sovereign AI infrastructure",
            "DARPA funding call for next-generation neural network security research",
            "Venture capital firm seeking to invest $50M in AI governance startups",
            "European Commission announces joint research initiative with US partners",
            "Fortune 500 company requests proposals for AI ethics consulting partnership",
        ]
        
        medium_opportunity = [
            "Local university interested in collaborative research on machine learning",
            "Startup looking for technical advisors in the AI space",
            "Non-profit organization seeking volunteers for AI policy work",
            "Industry conference looking for speakers on neural networks",
            "Tech blog requesting guest articles on AI safety",
            "Online course platform wants content on constitutional AI",
        ]
        
        low_opportunity = [
            "Random email asking for free consultation",
            "Spam message about investment opportunities",
            "Unsolicited request for partnership with no details",
            "Social media comment mentioning collaboration",
            "News article about AI with no actionable items",
        ]
        
        # Labels: [opportunity_score, urgency, type_strategic, type_academic, type_gov, type_industry, type_research, type_funding]
        high_labels = np.array([
            [0.95, 0.90, 0.3, 0.2, 0.0, 0.4, 0.9, 0.8],  # Anthropic - research/funding
            [0.92, 0.85, 0.4, 0.1, 0.9, 0.2, 0.7, 0.6],  # Pentagon - gov/strategic
            [0.88, 0.70, 0.2, 0.9, 0.1, 0.1, 0.9, 0.9],  # NSF - academic/funding
            [0.85, 0.60, 0.8, 0.1, 0.1, 0.9, 0.3, 0.5],  # Tech company - strategic/industry
            [0.90, 0.80, 0.3, 0.2, 0.9, 0.1, 0.9, 0.7],  # DARPA - gov/research
            [0.87, 0.65, 0.5, 0.1, 0.1, 0.7, 0.2, 0.9],  # VC - funding/industry
            [0.82, 0.55, 0.4, 0.7, 0.5, 0.2, 0.8, 0.6],  # EU Commission - mixed
            [0.80, 0.50, 0.6, 0.2, 0.1, 0.9, 0.2, 0.4],  # Fortune 500 - strategic/industry
        ])
        
        medium_labels = np.array([
            [0.60, 0.40, 0.2, 0.7, 0.0, 0.1, 0.6, 0.2],
            [0.55, 0.35, 0.3, 0.2, 0.0, 0.6, 0.3, 0.1],
            [0.50, 0.30, 0.1, 0.3, 0.1, 0.2, 0.4, 0.1],
            [0.45, 0.25, 0.2, 0.3, 0.0, 0.3, 0.2, 0.1],
            [0.40, 0.20, 0.1, 0.2, 0.0, 0.2, 0.3, 0.0],
            [0.48, 0.30, 0.2, 0.6, 0.0, 0.2, 0.5, 0.1],
        ])
        
        low_labels = np.array([
            [0.15, 0.10, 0.1, 0.0, 0.0, 0.1, 0.0, 0.0],
            [0.10, 0.15, 0.1, 0.0, 0.0, 0.1, 0.0, 0.1],
            [0.08, 0.05, 0.1, 0.0, 0.0, 0.1, 0.0, 0.0],
            [0.12, 0.08, 0.1, 0.1, 0.0, 0.1, 0.1, 0.0],
            [0.05, 0.05, 0.0, 0.1, 0.0, 0.0, 0.1, 0.0],
        ])
        
        all_texts = high_opportunity + medium_opportunity + low_opportunity
        all_labels = np.vstack([high_labels, medium_labels, low_labels])
        
        return all_texts, all_labels
    
    def train_model(self, training_data: Optional[Any] = None) -> Dict[str, float]:
        """Train the partnership detection model"""
        
        texts, labels = self._generate_training_data()
        
        # Ingest new samples from continual learning pipeline
        if training_data:
            new_texts = [t for t in training_data if isinstance(t, str) and len(t.strip()) > 10]
            if new_texts:
                median_label = np.median(labels, axis=0, keepdims=True).repeat(len(new_texts), axis=0)
                texts = list(texts) + new_texts
                labels = np.vstack([labels, median_label])
        
        # Fit vectorizer
        X_tfidf = self.vectorizer.fit_transform(texts).toarray()
        
        # Add keyword boost feature
        boosts = []
        for text in texts:
            text_lower = text.lower()
            boost = 0.0
            for keyword, weight in self.high_value_keywords.items():
                if keyword in text_lower:
                    boost += weight
            boosts.append(min(boost, 1.0))
        
        X = np.column_stack([X_tfidf, boosts])
        y = labels
        
        # Create and train MLP
        self.model = MLPRegressor(
            hidden_layer_sizes=(128, 64),
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
        
        self.metrics = {
            "mse": float(mse),
            "mae": float(mae),
            "training_samples": len(texts),
            "input_features": X.shape[1],
            "output_dimensions": y.shape[1]
        }
        self.is_trained = True
        
        return self.metrics
    
    def predict(self, text) -> Dict[str, Any]:
        """Detect partnership opportunities in text. Accepts str or dict with text_a/text_b."""
        if not self.is_trained or self.model is None:
            return {"error": "Model not trained", "opportunity_score": 0.5, "urgency": {"level": 0.5, "label": "unknown"}}

        # Handle dual-text input from SOV3 convergence scoring
        if isinstance(text, dict):
            text = f"{text.get('text_a', '')} {text.get('text_b', '')}"

        features = self.safe_features(self.extract_features(text)).reshape(1, -1)
        prediction = self.model.predict(features)[0]
        
        opportunity_score = float(prediction[0])
        urgency_level = float(prediction[1])
        type_scores = prediction[2:]
        
        # Determine primary type
        type_idx = np.argmax(type_scores)
        primary_type = self.partnership_types[type_idx]
        
        # Determine urgency label
        if urgency_level >= 0.7:
            urgency_label = "critical"
        elif urgency_level >= 0.5:
            urgency_label = "high"
        elif urgency_level >= 0.3:
            urgency_label = "medium"
        else:
            urgency_label = "low"
        
        return {
            "opportunity_score": round(opportunity_score, 3),
            "urgency": {
                "level": round(urgency_level, 3),
                "label": urgency_label
            },
            "partnership_type": {
                "primary": primary_type,
                "scores": {
                    t: round(float(s), 3) 
                    for t, s in zip(self.partnership_types, type_scores)
                }
            },
            "action_recommended": opportunity_score >= 0.6 and urgency_level >= 0.4
        }
    
if __name__ == "__main__":
    model = PartnershipDetectionML(model_dir="../models")
    metrics = model.train_model()
    print(f"Training metrics: {metrics}")
    
    test_texts = [
        "Anthropic just announced a $50M fund for AI safety research partnerships",
        "Local coffee shop looking for social media help",
    ]
    
    for text in test_texts:
        result = model.predict(text)
        print(f"\nText: {text}")
        print(f"Result: {result}")
