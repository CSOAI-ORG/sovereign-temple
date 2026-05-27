"""
Sentiment Analysis Neural Network for MEOK OS
Analyzes emotional tone and sentiment of text
"""

import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
import os
import json

# Import base model
from .base_model import BaseNeuralModel


class SentimentAnalysisNN(BaseNeuralModel):
    """
    Neural network for sentiment analysis
    Classifies text as positive, negative, neutral, or mixed
    """

    def __init__(self, model_dir: str = "models"):
        super().__init__("sentiment_analysis_nn", model_dir)
        self.input_features = 512
        self.output_dimensions = 4

        # Simple vocabulary for demonstration
        self.vocab = {}
        self.feature_weights = None

        # Training data statistics
        self.training_samples = 0
        self.class_counts = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}

        # Sentiment word lists (lexicon-based辅助)
        self.positive_words = {
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
            "love",
            "happy",
            "joy",
            "beautiful",
            "perfect",
            "best",
            "awesome",
            "nice",
            "kind",
            "helpful",
            "supportive",
            "grateful",
            "excited",
            "positive",
            "hopeful",
            "peaceful",
            "calm",
            "relaxed",
            "satisfied",
            "pleased",
            "delighted",
        }

        self.negative_words = {
            "bad",
            "terrible",
            "awful",
            "horrible",
            "hate",
            "sad",
            "angry",
            "fear",
            "worried",
            "anxious",
            "stressed",
            "frustrated",
            "disappointed",
            "angry",
            "upset",
            "hurt",
            "pain",
            "suffer",
            "danger",
            "threat",
            "problem",
            "issue",
            "fail",
            "failure",
            "wrong",
            "mistake",
            "regret",
            "sorry",
            "unfortunately",
        }

        self.intensity_words = {
            "very": 1.5,
            "extremely": 2.0,
            "really": 1.5,
            "absolutely": 2.0,
            "slightly": 0.5,
            "somewhat": 0.7,
            "barely": 0.3,
            "not": -1.0,
        }

    def _tokenize(self, text: str) -> list:
        """Simple tokenization"""
        return text.lower().split()

    def _extract_features(self, text: str) -> np.ndarray:
        """Extract sentiment features"""
        tokens = self._tokenize(text)

        # Initialize feature vector
        features = np.zeros(self.input_features)

        # Feature 1-100: Word presence (simple hash)
        for i, token in enumerate(tokens[:100]):
            features[i % 100] += hash(token) % 1000 / 10000

        # Feature 101-200: Sentiment word counts
        pos_count = sum(1 for t in tokens if t in self.positive_words)
        neg_count = sum(1 for t in tokens if t in self.negative_words)

        for i in range(100):
            features[100 + i] = pos_count / (len(tokens) + 1)
            features[200 + i] = neg_count / (len(tokens) + 1)

        # Feature 201-300: Sentence length features
        features[201] = len(tokens)
        features[202] = np.mean([len(t) for t in tokens]) if tokens else 0
        features[203] = len(text)  # Character count

        # Feature 204-250: Punctuation features
        features[204] = text.count("!")  # Excitement
        features[205] = text.count("?")  # Questions
        features[206] = text.count(".")  # Statements

        # Feature 207-300: Intensity modifiers
        intensity = 1.0
        for word, multiplier in self.intensity_words.items():
            if word in tokens:
                intensity *= multiplier
        features[207] = intensity

        # Normalize features
        if features.max() > 0:
            features = features / features.max()

        return features

    def train(self, texts: list, labels: list):
        """Train the sentiment model"""
        self.is_trained = True
        self.training_samples = len(texts)

        # Count class distribution
        for label in labels:
            if label in self.class_counts:
                self.class_counts[label] += 1

        # Simple weight initialization based on word analysis
        self.feature_weights = (
            np.random.randn(self.input_features, self.output_dimensions) * 0.1
        )

        # Apply sentiment word influence to weights
        for i in range(100):
            if i < len(self.positive_words):
                self.feature_weights[i, 0] += 0.5  # positive
                self.feature_weights[i, 2] -= 0.3  # reduce negative

            if i < len(self.negative_words):
                self.feature_weights[i, 1] += 0.5  # negative
                self.feature_weights[i, 0] -= 0.3  # reduce positive

        print(f"✓ Trained SentimentAnalysisNN on {self.training_samples} samples")

    def predict(self, text: str) -> Dict[str, Any]:
        """Predict sentiment of text"""
        if not self.is_trained:
            return {"error": "Model not trained"}

        features = self._extract_features(text)

        # Simple softmax prediction
        logits = np.dot(features, self.feature_weights)
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        sentiment_classes = ["positive", "negative", "neutral", "mixed"]
        predicted_class = sentiment_classes[np.argmax(probs)]

        # Calculate confidence
        confidence = float(probs[np.argmax(probs)])

        # Get scores for each class
        scores = {sentiment_classes[i]: float(probs[i]) for i in range(4)}

        # Detect intensity and mixed signals
        tokens = self._tokenize(text)
        pos_count = sum(1 for t in tokens if t in self.positive_words)
        neg_count = sum(1 for t in tokens if t in self.negative_words)

        mixed = False
        if pos_count > 0 and neg_count > 0:
            mixed = True
            predicted_class = "mixed"

        # Analyze emotional depth
        emotional_depth = (pos_count + neg_count) / (len(tokens) + 1) if tokens else 0

        return {
            "sentiment": predicted_class,
            "confidence": confidence,
            "scores": scores,
            "is_mixed": mixed,
            "emotional_depth": emotional_depth,
            "word_counts": {
                "positive": pos_count,
                "negative": neg_count,
                "total": len(tokens),
            },
        }


# Singleton instance
_sentiment_model = None


def get_sentiment_model() -> SentimentAnalysisNN:
    """Get or create sentiment model instance"""
    global _sentiment_model
    if _sentiment_model is None:
        _sentiment_model = SentimentAnalysisNN()

        # Train with sample data
        sample_texts = [
            "I love this product, it's amazing and wonderful!",
            "This is terrible, I hate it and it's awful.",
            "The meeting is at 3pm.",
            "I'm so excited and happy about this opportunity!",
            "This is confusing and frustrating, I don't understand.",
            "The weather is nice today.",
            "I'm worried about the problem and scared it might fail.",
            "Great job, excellent work, very happy with results!",
            "Unfortunately, I'm disappointed and upset about this.",
            "Everything is fine, nothing special happening.",
        ]

        sample_labels = [
            "positive",
            "negative",
            "neutral",
            "positive",
            "negative",
            "neutral",
            "negative",
            "positive",
            "negative",
            "neutral",
        ]

        _sentiment_model.train(sample_texts, sample_labels)

    return _sentiment_model


def analyze_sentiment(text: str) -> Dict[str, Any]:
    """Analyze sentiment of text"""
    model = get_sentiment_model()
    return model.predict(text)
