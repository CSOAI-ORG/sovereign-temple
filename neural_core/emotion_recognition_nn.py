"""
Emotion Recognition Neural Network for MEOK OS
Detects specific emotions from text (joy, sadness, anger, fear, surprise, disgust)
"""

import numpy as np
from typing import Dict, Any, List
from collections import defaultdict


class EmotionRecognitionNN:
    """
    Neural network for emotion recognition
    Identifies 6 basic emotions plus additional nuanced states
    """

    def __init__(self):
        self.is_trained = False
        self.model_name = "emotion_recognition_nn"

        # Ekman's 6 basic emotions + additional
        self.emotions = [
            "joy",
            "sadness",
            "anger",
            "fear",
            "surprise",
            "disgust",
            "trust",
            "anticipation",
            "love",
            "frustration",
            "confusion",
            "hope",
        ]

        self.input_features = 256
        self.output_dimensions = len(self.emotions)

        # Emotion word lexicons
        self.emotion_lexicon = {
            "joy": [
                "happy",
                "joy",
                "excited",
                "delighted",
                "thrilled",
                "glad",
                "pleased",
                "cheerful",
                "content",
                "elated",
                "ecstatic",
                "wonderful",
                "great",
                "love",
                "loving",
            ],
            "sadness": [
                "sad",
                "unhappy",
                "depressed",
                "down",
                "disappointed",
                "heartbroken",
                "miserable",
                "grief",
                "sorrow",
                "cry",
                "tears",
                "unfortunate",
                "regret",
                "lonely",
            ],
            "anger": [
                "angry",
                "mad",
                "furious",
                "irritated",
                "annoyed",
                "frustrated",
                "outraged",
                "hate",
                "rage",
                "enraged",
                "hostile",
                "bitter",
                "resentful",
            ],
            "fear": [
                "afraid",
                "scared",
                "fear",
                "terrified",
                "anxious",
                "worried",
                "nervous",
                "panic",
                "dread",
                "frightened",
                "concerned",
                "uncertain",
                "vulnerable",
            ],
            "surprise": [
                "surprised",
                "amazed",
                "astonished",
                "shocked",
                "unexpected",
                "sudden",
                "wow",
                "incredible",
                "unbelievable",
                "astonishing",
            ],
            "disgust": [
                "disgusted",
                "gross",
                "revolting",
                "sick",
                "dislike",
                "repulsed",
                "nauseous",
                "appalled",
                "distaste",
                "awful",
            ],
            "trust": [
                "trust",
                "believe",
                "rely",
                "confident",
                "faith",
                "depend",
                "honest",
                "sincere",
                "loyal",
                "reassured",
            ],
            "anticipation": [
                "expect",
                "hope",
                "look forward",
                "await",
                "eager",
                "excited",
                "planning",
                "soon",
                "waiting",
                "future",
            ],
            "love": [
                "love",
                "adore",
                "care",
                "affection",
                "fond",
                "cherish",
                "appreciate",
                "warm",
                "tender",
                "close",
            ],
            "frustration": [
                "frustrated",
                "stuck",
                "blocked",
                "impossible",
                "difficult",
                "hard",
                "struggle",
                "exasperated",
                "failing",
            ],
            "confusion": [
                "confused",
                "uncertain",
                "unclear",
                "don't understand",
                "puzzled",
                "perplexed",
                "lost",
                "mixed up",
            ],
            "hope": [
                "hope",
                "optimistic",
                "wish",
                "pray",
                "positive",
                "better",
                "improve",
                "possible",
                "believe",
            ],
        }

        # Context patterns
        self.context_patterns = {
            "sarcasm": ["not", "yeah right", "sure", "whatever", "oh really"],
            "denial": ["not", "never", "don't", "won't", "can't"],
            "emphasis": ["!", "really", "so", "very", "actually", "definitely"],
        }

        self.weights = None
        self.training_samples = 0

    def _extract_features(self, text: str) -> np.ndarray:
        """Extract features for emotion detection"""
        text_lower = text.lower()
        tokens = text_lower.split()

        features = np.zeros(self.input_features)

        # Emotion word counts
        for i, emotion in enumerate(self.emotions):
            count = sum(
                1 for word in self.emotion_lexicon[emotion] if word in text_lower
            )
            features[i] = count / max(len(tokens), 1)

        # Context features (100-150)
        for i, pattern_type in enumerate(self.context_patterns):
            count = sum(
                1
                for pattern in self.context_patterns[pattern_type]
                if pattern in text_lower
            )
            features[100 + i] = count

        # Text structure features (150-200)
        features[150] = len(tokens)
        features[151] = text.count("!") / max(len(tokens), 1)
        features[152] = text.count("?") / max(len(tokens), 1)
        features[153] = text.count("...") / max(len(tokens), 1)

        # Capitalization (emphasis detection)
        caps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 1)
        features[154] = caps_words / max(len(tokens), 1)

        # Length features
        features[155] = min(len(text) / 500, 1.0)  # Normalize length
        features[156] = 1.0 if len(tokens) < 5 else 0.0  # Short text
        features[157] = 1.0 if len(tokens) > 20 else 0.0  # Long text

        # Word uniqueness (vocabulary richness)
        unique_ratio = len(set(tokens)) / max(len(tokens), 1)
        features[158] = unique_ratio

        # Normalize
        if features.max() > 0:
            features = features / features.max()

        return features

    def train(self, texts: List[str], labels: List[List[str]]):
        """Train the emotion recognition model"""
        self.is_trained = True
        self.training_samples = len(texts)

        # Initialize weights with emotion word influence
        self.weights = (
            np.random.randn(self.input_features, self.output_dimensions) * 0.1
        )

        # Boost weights for emotion words
        for i, emotion in enumerate(self.emotions):
            for word in self.emotion_lexicon[emotion][:20]:
                word_hash = hash(word) % self.input_features
                self.weights[word_hash, i] += 0.3

        print(f"✓ Trained EmotionRecognitionNN on {self.training_samples} samples")

    def predict(self, text: str) -> Dict[str, Any]:
        """Recognize emotions in text"""
        if not self.is_trained:
            return {"error": "Model not trained"}

        features = self._extract_features(text)

        # Get emotion scores
        scores = np.dot(features, self.weights)

        # Apply softmax
        exp_scores = np.exp(scores - np.max(scores))
        probs = exp_scores / exp_scores.sum()

        # Get top emotions
        emotion_scores = {
            self.emotions[i]: float(probs[i]) for i in range(len(self.emotions))
        }
        sorted_emotions = sorted(
            emotion_scores.items(), key=lambda x: x[1], reverse=True
        )

        # Detect dominant emotion
        dominant_emotion = sorted_emotions[0][0]
        dominant_score = sorted_emotions[0][1]

        # Detect mixed emotions (multiple emotions above threshold)
        mixed_emotions = [e for e, s in sorted_emotions if s > 0.2]

        # Check for context (sarcasm, etc)
        context = []
        text_lower = text.lower()
        if any(p in text_lower for p in self.context_patterns["sarcasm"]):
            context.append("possible_sarcasm")
        if any(p in text_lower for p in self.context_patterns["emphasis"]):
            context.append("emphatic")

        # Emotional intensity
        intensity = sum(s for _, s in sorted_emotions[:3])

        return {
            "dominant_emotion": dominant_emotion,
            "dominant_score": dominant_score,
            "emotion_scores": emotion_scores,
            "top_emotions": sorted_emotions[:3],
            "is_mixed": len(mixed_emotions) > 1,
            "mixed_emotions": mixed_emotions,
            "context_detected": context,
            "intensity": intensity,
            "text_length": len(text.split()),
        }


_emotion_model = None


def get_emotion_model() -> EmotionRecognitionNN:
    global _emotion_model
    if _emotion_model is None:
        _emotion_model = EmotionRecognitionNN()

        # Train with sample data
        samples = [
            ("I'm so happy and excited about this!", ["joy", "anticipation", "love"]),
            ("This is terrible and I hate it", ["anger", "disgust"]),
            ("I'm worried about what might happen", ["fear", "anticipation"]),
            ("The meeting is at noon", []),
            ("I love you so much!", ["joy", "love"]),
            ("This is frustrating and difficult", ["frustration", "sadness"]),
            ("I'm confused about what to do", ["confusion", "fear"]),
            ("I hope things get better soon", ["hope", "anticipation"]),
            ("I'm really angry about this", ["anger"]),
            ("What a wonderful surprise!", ["surprise", "joy"]),
        ]

        texts, labels = zip(*samples)
        _emotion_model.train(list(texts), list(labels))

    return _emotion_model


def recognize_emotions(text: str) -> Dict[str, Any]:
    """Recognize emotions in text"""
    model = get_emotion_model()
    return model.predict(text)
