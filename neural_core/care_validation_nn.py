"""
Care Validation Neural Network
Validates interactions against care-centered principles
Architecture: 256 -> 128 -> 64 -> 6 outputs
"""

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import Dict, Any, List, Optional
from . import base_model
import pickle
import os


class CareValidationNN(base_model.BaseNeuralModel):
    """
    Neural network for validating care-centered interactions
    Outputs 6 dimension scores: empathy, respect, constructiveness, 
    inclusivity, emotional_safety, honesty_with_kindness
    """
    
    def __init__(self, model_dir: str = "models"):
        super().__init__("care_validation_nn", model_dir)
        self.vectorizer = TfidfVectorizer(max_features=256, stop_words='english')
        self.care_dimensions = [
            "empathy",
            "respect", 
            "constructiveness",
            "inclusivity",
            "emotional_safety",
            "honesty_with_kindness"
        ]
    
    def extract_features(self, text: str) -> np.ndarray:
        """Extract TF-IDF features from text"""
        if not hasattr(self.vectorizer, 'vocabulary_'):
            # Vectorizer not fitted yet, return zeros
            return np.zeros(256)
        return self.vectorizer.transform([text]).toarray()[0]
    
    def _generate_training_data(self) -> tuple:
        """Generate synthetic training data for care validation"""
        
        high_care_examples = [
            "I understand this is difficult for you. Let's work through it together.",
            "Your perspective matters to me. Can you help me understand your view?",
            "Thank you for sharing that. I appreciate your honesty and vulnerability.",
            "Let's find a solution that works for everyone involved.",
            "I respect your boundaries and want to support you in the way you need.",
            "That sounds really challenging. I'm here to listen if you want to talk.",
            "Your feelings are valid. It's okay to feel that way.",
            "I appreciate you trusting me with this information.",
        ]
        
        medium_care_examples = [
            "I see your point, but I think we should consider other options.",
            "That's one way to look at it, though there might be another perspective.",
            "I understand what you're saying. Here's my take on it.",
            "Let's try to be objective about this situation.",
            "I hear you, and I also want to mention...",
        ]
        
        low_care_examples = [
            "You're completely wrong about that.",
            "That's a stupid idea and you should know better.",
            "I don't care what you think, just do what I say.",
            "You're being too sensitive. Get over it.",
            "That's not my problem. Deal with it yourself.",
            "You're overreacting. It's not that big of a deal.",
        ]
        
        # High care labels (0.8-1.0 for all dimensions)
        high_labels = np.array([
            [0.95, 0.90, 0.92, 0.88, 0.93, 0.91],
            [0.88, 0.92, 0.85, 0.90, 0.87, 0.86],
            [0.90, 0.88, 0.87, 0.85, 0.92, 0.94],
            [0.85, 0.86, 0.93, 0.95, 0.84, 0.88],
            [0.87, 0.94, 0.89, 0.86, 0.90, 0.85],
            [0.93, 0.87, 0.86, 0.88, 0.94, 0.89],
            [0.91, 0.89, 0.84, 0.87, 0.91, 0.87],
            [0.89, 0.91, 0.88, 0.86, 0.89, 0.92],
        ])
        
        # Medium care labels (0.5-0.7 for all dimensions)
        medium_labels = np.array([
            [0.65, 0.60, 0.55, 0.62, 0.58, 0.64],
            [0.58, 0.62, 0.56, 0.60, 0.55, 0.61],
            [0.62, 0.58, 0.60, 0.57, 0.63, 0.59],
            [0.55, 0.65, 0.58, 0.54, 0.60, 0.62],
            [0.60, 0.57, 0.62, 0.59, 0.61, 0.56],
        ])
        
        # Low care labels (0.1-0.3 for all dimensions)
        low_labels = np.array([
            [0.15, 0.20, 0.12, 0.18, 0.10, 0.14],
            [0.10, 0.15, 0.08, 0.12, 0.09, 0.11],
            [0.08, 0.12, 0.15, 0.10, 0.11, 0.13],
            [0.12, 0.18, 0.10, 0.14, 0.08, 0.16],
            [0.14, 0.11, 0.13, 0.16, 0.12, 0.10],
            [0.11, 0.14, 0.09, 0.13, 0.15, 0.12],
        ])
        
        all_texts = high_care_examples + medium_care_examples + low_care_examples
        all_labels = np.vstack([high_labels, medium_labels, low_labels])
        
        return all_texts, all_labels
    
    def train_model(self, training_data: Optional[Any] = None) -> Dict[str, float]:
        """Train the care validation neural network"""
        
        texts, labels = self._generate_training_data()
        
        # Ingest new samples from continual learning pipeline
        if training_data:
            new_texts = [t for t in training_data if isinstance(t, str) and len(t.strip()) > 10]
            if new_texts:
                median_label = np.median(labels, axis=0, keepdims=True).repeat(len(new_texts), axis=0)
                texts = list(texts) + new_texts
                labels = np.vstack([labels, median_label])
        
        # Fit vectorizer
        X = self.vectorizer.fit_transform(texts).toarray()
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
    
    def predict(self, text: str) -> Dict[str, Any]:
        """Predict care scores for input text"""
        if not self.is_trained or self.model is None:
            return {"error": "Model not trained", "overall_care_score": 0.5, "assessment": "uncertain"}

        features = self.safe_features(self.extract_features(text)).reshape(1, -1)
        scores = self.model.predict(features)[0]
        
        # Overall care score is weighted average
        weights = [0.20, 0.18, 0.18, 0.15, 0.15, 0.14]
        overall_score = sum(s * w for s, w in zip(scores, weights))
        
        return {
            "overall_care_score": round(overall_score, 3),
            "dimension_scores": {
                dim: round(score, 3) 
                for dim, score in zip(self.care_dimensions, scores)
            },
            "assessment": self._assess_care_level(overall_score)
        }
    
    def _assess_care_level(self, score: float) -> str:
        """Convert score to care level assessment"""
        if score >= 0.8:
            return "exemplary_care"
        elif score >= 0.6:
            return "good_care"
        elif score >= 0.4:
            return "moderate_care"
        elif score >= 0.2:
            return "care_needed"
        else:
            return "care_critical"
    
    def save_model(self) -> bool:
        """Save model and vectorizer to disk"""
        try:
            # Save the base model
            base_result = super().save_model()
            
            # Save the vectorizer
            vectorizer_path = os.path.join(self.model_dir, f"{self.model_name}_vectorizer.pkl")
            if self.vectorizer is not None and hasattr(self.vectorizer, 'vocabulary_'):
                with open(vectorizer_path, 'wb') as f:
                    pickle.dump(self.vectorizer, f)
                return True and base_result
        except Exception as e:
            print(f"Error saving model {self.model_name}: {e}")
        return False
    
    def load_model(self) -> bool:
        """Load model and vectorizer from disk"""
        try:
            # Load the base model
            base_result = super().load_model()
            
            # Load the vectorizer
            vectorizer_path = os.path.join(self.model_dir, f"{self.model_name}_vectorizer.pkl")
            if os.path.exists(vectorizer_path):
                with open(vectorizer_path, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                return True and base_result
        except Exception as e:
            print(f"Error loading model {self.model_name}: {e}")
        return False


if __name__ == "__main__":
    # Test the model
    model = CareValidationNN(model_dir="../models")
    metrics = model.train_model()
    print(f"Training metrics: {metrics}")
    
    # Test predictions
    test_texts = [
        "I really appreciate you taking the time to explain this to me.",
        "That's the dumbest thing I've ever heard."
    ]
    
    for text in test_texts:
        result = model.predict(text)
        print(f"\nText: {text}")
        print(f"Result: {result}")
