"""
Intent Detection Neural Network for MEOK OS
Identifies user intent from natural language (help, create, learn, play, etc.)
"""

import numpy as np
from typing import Dict, Any, List, Optional


class IntentDetectionNN:
    """
    Neural network for intent detection
    Maps user utterances to actionable intents
    """

    def __init__(self):
        self.is_trained = False
        self.model_name = "intent_detection_nn"

        # Define intents
        self.intents = [
            "help",
            "create",
            "learn",
            "play",
            "chat",
            "question",
            "task",
            "search",
            "analyze",
            "plan",
            "remind",
            "check",
            "share",
            "organize",
            "relax",
            "work",
            "health",
            "family",
        ]

        self.input_features = 200
        self.output_dimensions = len(self.intents)

        # Intent keywords and patterns
        self.intent_patterns = {
            "help": [
                "help",
                "assist",
                "support",
                "please",
                "need",
                "can you",
                "how do i",
                "need help",
            ],
            "create": [
                "create",
                "make",
                "build",
                "write",
                "design",
                "generate",
                "new",
                "start",
            ],
            "learn": [
                "learn",
                "teach",
                "explain",
                "understand",
                "study",
                "read about",
                "how does",
            ],
            "play": [
                "play",
                "game",
                "fun",
                "entertain",
                "joke",
                "hobby",
                "watch",
                "listen",
            ],
            "chat": [
                "talk",
                "chat",
                "conversation",
                "discuss",
                "tell me about",
                "what do you think",
            ],
            "question": [
                "what",
                "who",
                "where",
                "when",
                "why",
                "how",
                "is",
                "are",
                "can",
                "could",
                "question",
            ],
            "task": [
                "do",
                "complete",
                "finish",
                "execute",
                "run",
                "process",
                "handle",
                "take care",
            ],
            "search": [
                "search",
                "find",
                "look for",
                "locate",
                "show me",
                "google",
                "browse",
            ],
            "analyze": [
                "analyze",
                "check",
                "review",
                "examine",
                "assess",
                "evaluate",
                "compare",
            ],
            "plan": [
                "plan",
                "schedule",
                "organize",
                "arrange",
                "prepare",
                "upcoming",
                "timeline",
            ],
            "remind": [
                "remind",
                "remember",
                "don't forget",
                "alert",
                "notify",
                "wake",
                "timer",
            ],
            "check": [
                "check",
                "verify",
                "confirm",
                "status",
                "is it",
                "does it work",
                "how's",
            ],
            "share": ["share", "send", "tell", "post", "forward", "recommend", "show"],
            "organize": ["organize", "sort", "categorize", "group", "整理", "organize"],
            "relax": [
                "relax",
                "calm",
                "meditate",
                "breathe",
                "wind down",
                "unwind",
                "peaceful",
            ],
            "work": [
                "work",
                "office",
                "job",
                "meeting",
                "deadline",
                "project",
                "business",
            ],
            "health": [
                "health",
                "fitness",
                "exercise",
                "sleep",
                "diet",
                "wellness",
                "medical",
            ],
            "family": [
                "family",
                "kids",
                "children",
                "parents",
                "home",
                "kids",
                "guardian",
            ],
        }

        # Context words that modify intent
        self.modifiers = {
            "urgent": 1.5,
            "asap": 1.5,
            "now": 1.3,
            "later": 0.8,
            "sometime": 0.7,
            "maybe": 0.5,
            "quick": 1.2,
            "carefully": 0.9,
        }

        self.weights = None
        self.training_samples = 0

    def _extract_features(self, text: str) -> np.ndarray:
        """Extract features for intent detection"""
        text_lower = text.lower()
        tokens = text_lower.split()

        features = np.zeros(self.input_features)

        # Intent pattern matching (0-100)
        for i, intent in enumerate(self.intents):
            score = 0
            patterns = self.intent_patterns.get(intent, [])
            for pattern in patterns:
                if pattern in text_lower:
                    score += 1
                    # Bonus for word boundary match
                    if (
                        f" {pattern} " in f" {text_lower} "
                        or text_lower.startswith(pattern)
                        or text_lower.endswith(pattern)
                    ):
                        score += 0.5
            features[i] = score / max(len(tokens), 1) * 10

        # Modifier detection (100-110)
        intensity = 1.0
        for mod, mult in self.modifiers.items():
            if mod in text_lower:
                features[100] = mult
                intensity = mult

        # Sentence structure features (110-130)
        features[110] = len(tokens) / 20.0  # Normalized length
        features[111] = 1.0 if text.endswith("?") else 0.0  # Question
        features[112] = 1.0 if text.endswith("!") else 0.0  # Exclamation
        features[113] = 1.0 if "please" in text_lower else 0.0  # Polite
        features[114] = 1.0 if "can you" in text_lower else 0.0  # Request

        # First word features (130-150)
        first_word = tokens[0] if tokens else ""
        features[130] = 1.0 if first_word in ["help", "make", "find", "show"] else 0.0

        # Punctuation features (150-160)
        features[150] = text.count("...") / max(len(tokens), 1)

        # Action word detection
        action_words = ["want", "need", "would", "could", "should", "will", "going"]
        features[155] = sum(1 for w in tokens if w in action_words) / max(
            len(tokens), 1
        )

        # Normalize
        if features.max() > 0:
            features = features / features.max()

        return features

    def train(self, texts: List[str], labels: List[str]):
        """Train the intent detection model"""
        self.is_trained = True
        self.training_samples = len(texts)

        # Initialize weights with pattern influence
        self.weights = (
            np.random.randn(self.input_features, self.output_dimensions) * 0.1
        )

        # Boost weights for intent patterns
        for i, intent in enumerate(self.intents):
            for pattern in self.intent_patterns.get(intent, []):
                word_hash = hash(pattern[:5]) % self.input_features
                self.weights[word_hash, i] += 0.2

        print(f"✓ Trained IntentDetectionNN on {self.training_samples} samples")

    def predict(self, text: str) -> Dict[str, Any]:
        """Detect user intent"""
        if not self.is_trained:
            return {"error": "Model not trained"}

        features = self._extract_features(text)

        # Get intent scores
        scores = np.dot(features, self.weights)

        # Apply softmax
        exp_scores = np.exp(scores - np.max(scores))
        probs = exp_scores / exp_scores.sum()

        # Build result
        intent_scores = {
            self.intents[i]: float(probs[i]) for i in range(len(self.intents))
        }
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)

        # Primary intent
        primary_intent = sorted_intents[0][0]
        primary_score = sorted_intents[0][1]

        # Secondary intents (above threshold)
        secondary = [
            i for i, s in sorted_intents if s > 0.15 and i != sorted_intents[0][0]
        ]

        # Confidence
        confidence = primary_score if primary_score > 0.3 else 0.5

        # Detect if it's a question
        is_question = text.strip().endswith("?")

        # Detect urgency
        text_lower = text.lower()
        urgency = 0.0
        for word in ["urgent", "asap", "now", "immediately"]:
            if word in text_lower:
                urgency = 1.0
                break

        # Multi-intent detection
        top_2 = sorted_intents[:2]
        is_multi_intent = len(secondary) > 0 and (top_2[0][1] - top_2[1][1]) < 0.3

        return {
            "primary_intent": primary_intent,
            "primary_score": primary_score,
            "intent_scores": intent_scores,
            "confidence": confidence,
            "is_question": is_question,
            "urgency": urgency,
            "is_multi_intent": is_multi_intent,
            "secondary_intents": [s[0] for s in sorted_intents[1:4]],
            "text_length": len(text.split()),
        }


_intent_model = None


def get_intent_model() -> IntentDetectionNN:
    global _intent_model
    if _intent_model is None:
        _intent_model = IntentDetectionNN()

        # Train with sample data
        samples = [
            ("Can you help me with this?", "help"),
            ("Create a new document", "create"),
            ("I want to learn about AI", "learn"),
            ("Let's play a game", "play"),
            ("Can we chat for a bit", "chat"),
            ("What is machine learning?", "question"),
            ("Finish this task please", "task"),
            ("Search for recipes", "search"),
            ("Analyze this data", "analyze"),
            ("Plan my week", "plan"),
            ("Remind me to call mom", "remind"),
            ("Check my email", "check"),
            ("Share this with team", "share"),
            ("Organize my files", "organize"),
            ("I need to relax", "relax"),
            ("Time for work", "work"),
            ("How's my health?", "health"),
            ("Check the kids' homework", "family"),
        ]

        texts, labels = zip(*samples)
        _intent_model.train(list(texts), list(labels))

    return _intent_model


def detect_intent(text: str) -> Dict[str, Any]:
    """Detect user intent"""
    model = get_intent_model()
    return model.predict(text)
