#!/usr/bin/env python3
"""
Dependency Detection Neural Network
Trains on text to detect dependency relationships for Maternal Covenant
Features:
- Identifies codependent patterns in text
- Analyzes relationship dynamics
- Detects over-giving vs healthy boundaries
- Provides actionable recommendations

Run: python dependency_detection_nn.py train
Run: python dependency_detection_nn.py predict "I always put everyone else's needs first"
"""

import json
import numpy as np
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Add paths
sys.path.insert(0, os.path.dirname(__file__))

try:
    from sklearn.neural_network import MLPClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: sklearn not available, using simple fallback")


@dataclass
class DependencyPattern:
    """Detected dependency pattern"""

    pattern_type: str  # codependent, enabling, healthy, distancing
    confidence: float
    evidence: List[str]
    recommendations: List[str]


class DependencyDetectionNN:
    """
    Neural network for detecting dependency patterns in text
    Used for Maternal Covenant care assessment
    """

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self.vectorizer = TfidfVectorizer(max_features=256, stop_words="english")
        self.model = None

        self.pattern_types = [
            "codependent",  # Excessive reliance on others for self-worth
            "enabling",  # Supporting harmful behavior patterns
            "healthy",  # Balanced, mutually supportive
            "distancing",  # Avoidant, fear-based boundaries
            "over-giving",  # Giving beyond healthy limits
            "people-pleasing",  # Constant approval-seeking
        ]

        self._ensure_model_dir()

    def _ensure_model_dir(self):
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir, exist_ok=True)

    def _generate_training_data(self) -> Tuple[List[str], List[int]]:
        """
        Generate synthetic training data for dependency detection
        In production, this would come from real user interactions
        """

        texts = []
        labels = []

        # Codependent examples (label 0)
        codependent_texts = [
            "I can't make decisions without checking with them first",
            "I feel lost when I'm not around my partner",
            "My happiness depends entirely on how they treat me",
            "I always put their needs before my own, even when it hurts me",
            "I don't know who I am without them",
            "I need their approval for everything I do",
            "I feel responsible for their emotions and happiness",
            "I can't say no to them, even when I want to",
            "I've given up my dreams to keep them happy",
            "I'm terrified of them leaving me",
        ]
        texts.extend(codependent_texts)
        labels.extend([0] * len(codependent_texts))

        # Enabling examples (label 1)
        enabling_texts = [
            "I always help them even when it enables bad behavior",
            "I make excuses for their actions",
            "I cover for them when they're not doing their share",
            "I keep quiet about problems to avoid conflict",
            "I let them use me because I don't want to upset them",
            "I bail them out every time they're in trouble",
            "I accept their excuses instead of holding them accountable",
        ]
        texts.extend(enabling_texts)
        labels.extend([1] * len(enabling_texts))

        # Healthy examples (label 2)
        healthy_texts = [
            "I set boundaries that work for both of us",
            "I can say no and still feel good about the relationship",
            "I take care of myself while supporting them",
            "I communicate my needs openly and respectfully",
            "I respect their autonomy while maintaining mine",
            "We support each other without losing ourselves",
            "I can be myself in this relationship",
            "I have my own life outside this relationship",
            "I give freely but not at my own expense",
            "I accept them as they are while growing myself",
        ]
        texts.extend(healthy_texts)
        labels.extend([2] * len(healthy_texts))

        # Distancing examples (label 3)
        distancing_texts = [
            "I keep everyone at arm's length to avoid getting hurt",
            "I push people away when they get too close",
            "I don't let anyone truly know me",
            "I prefer to handle everything on my own",
            "I don't need anyone - I'm fine by myself",
            "I cancel plans when things get too personal",
            "I change the subject when conversations get deep",
        ]
        texts.extend(distancing_texts)
        labels.extend([3] * len(distancing_texts))

        # Over-giving examples (label 4)
        overgiving_texts = [
            "I give and give but never receive",
            "I exhaust myself helping everyone else",
            "I always pick up the slack for others",
            "I do everything myself because no one else will",
            "I put everyone else's needs above my own health",
            "I can't stop over-committing myself",
            "I feel guilty when I take time for myself",
            "I overdo it until I burn out",
        ]
        texts.extend(overgiving_texts)
        labels.extend([4] * len(overgiving_texts))

        # People-pleasing examples (label 5)
        peoplepleasing_texts = [
            "I agree with everything to avoid disagreement",
            "I pretend to agree even when I don't",
            "I can't handle criticism - it devastates me",
            "I change myself to be what others want",
            "I feel like an imposter around others",
            "I say yes when I mean no",
            "I base my worth on others' approval",
            "I'm terrified of disappointing anyone",
        ]
        texts.extend(peoplepleasing_texts)
        labels.extend([5] * len(peoplepleasing_texts))

        return texts, labels

    def train(self, test_size: float = 0.2) -> Dict:
        """Train the dependency detection model"""

        if not SKLEARN_AVAILABLE:
            return {"status": "skipped", "reason": "sklearn not available"}

        print("Generating training data...")
        texts, labels = self._generate_training_data()

        # Vectorize
        print("Vectorizing text...")
        X = self.vectorizer.fit_transform(texts).toarray()
        y = np.array(labels)

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Train
        print("Training model...")
        self.model = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
        )
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        # Save model
        self._save_model()

        return {
            "status": "trained",
            "accuracy": accuracy,
            "train_size": len(X_train),
            "test_size": len(X_test),
            "classes": self.pattern_types,
        }

    def _save_model(self):
        """Save model and vectorizer"""
        import pickle

        model_path = os.path.join(self.model_dir, "dependency_detection_model.pkl")
        vectorizer_path = os.path.join(
            self.model_dir, "dependency_detection_vectorizer.pkl"
        )

        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)
        with open(vectorizer_path, "wb") as f:
            pickle.dump(self.vectorizer, f)

        print(f"Model saved to {self.model_dir}")

    def load_model(self) -> bool:
        """Load saved model"""
        import pickle

        model_path = os.path.join(self.model_dir, "dependency_detection_model.pkl")
        vectorizer_path = os.path.join(
            self.model_dir, "dependency_detection_vectorizer.pkl"
        )

        if not os.path.exists(model_path):
            return False

        try:
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)
            with open(vectorizer_path, "rb") as f:
                self.vectorizer = pickle.load(f)
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def predict(self, text: str) -> DependencyPattern:
        """Predict dependency pattern in text"""

        if self.model is None and not self.load_model():
            # Return default if no model
            return DependencyPattern(
                pattern_type="unknown",
                confidence=0.0,
                evidence=["Model not loaded"],
                recommendations=["Train the model first"],
            )

        # Vectorize
        X = self.vectorizer.transform([text]).toarray()

        # Predict
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        confidence = float(probabilities[prediction])

        pattern_type = self.pattern_types[prediction]

        # Generate evidence and recommendations
        evidence = self._extract_evidence(text, pattern_type)
        recommendations = self._get_recommendations(pattern_type)

        return DependencyPattern(
            pattern_type=pattern_type,
            confidence=confidence,
            evidence=evidence,
            recommendations=recommendations,
        )

    def _extract_evidence(self, text: str, pattern_type: str) -> List[str]:
        """Extract evidence for the detected pattern"""
        text_lower = text.lower()
        evidence = []

        evidence_keywords = {
            "codependent": ["can't", "need", "depend", "without", "lost", "terrified"],
            "enabling": ["excuse", "cover", "avoid conflict", "bail out", "keep quiet"],
            "healthy": ["boundary", "respect", "communicate", "autonomy", "support"],
            "distancing": ["keep", "push away", "fine by myself", "don't need"],
            "over-giving": ["give and give", "exhaust", "burn out", "pick up slack"],
            "people-pleasing": [
                "agree",
                "can't say no",
                "terrified",
                "imposter",
                "approval",
            ],
        }

        keywords = evidence_keywords.get(pattern_type, [])
        for keyword in keywords:
            if keyword in text_lower:
                evidence.append(f"Found: '{keyword}'")

        if not evidence:
            evidence.append(f"Pattern analysis based on: {text[:50]}...")

        return evidence

    def _get_recommendations(self, pattern_type: str) -> List[str]:
        """Get recommendations based on pattern type"""

        recommendations = {
            "codependent": [
                "Practice identifying your own needs separate from others",
                "Start small: make one decision today based solely on your preference",
                "Consider therapy to explore the root of this pattern",
                "Build your own identity through hobbies and friendships",
            ],
            "enabling": [
                "Start practicing quiet accountability in small ways",
                "Ask yourself: 'Am I helping or just making them comfortable?'",
                "Let natural consequences happen where safe",
                "Get support for your own boundaries",
            ],
            "healthy": [
                "Continue nurturing these balanced patterns",
                "Share what works with others seeking healthy relationships",
                "Check in regularly that you're still honoring your needs too",
            ],
            "distancing": [
                "Challenge yourself to one small vulnerability today",
                "Notice what you're afraid will happen if you let someone in",
                "Remember: healthy connection protects you, not endangers you",
                "Consider what 'being fine by yourself' is costing you",
            ],
            "over-giving": [
                "Notice the feeling before you say yes - what's really driving it?",
                "Practice 'I'll think about it' before automatically agreeing",
                "Schedule recovery time after giving",
                "Ask: 'What do I need?' before asking what others need",
            ],
            "people-pleasing": [
                "Practice stating small disagreements",
                "Notice when you say yes but feel no",
                "Your worth isn't determined by others' approval",
                "Start with 'I'll get back to you' instead of immediate yes",
            ],
        }

        return recommendations.get(pattern_type, ["Keep reflecting on your patterns"])

    def batch_predict(self, texts: List[str]) -> List[DependencyPattern]:
        """Predict patterns for multiple texts"""
        return [self.predict(text) for text in texts]

    def get_care_weight_adjustment(self, text: str) -> float:
        """
        Get care weight adjustment for Maternal Covenant
        Returns: adjustment amount (-1.0 to +1.0)
        """
        pattern = self.predict(text)

        # Adjustments based on pattern
        adjustments = {
            "codependent": -0.3,  # Reduce over-giving care
            "enabling": -0.2,  # Reduce enabling care
            "healthy": +0.1,  # Support healthy patterns
            "distancing": +0.05,  # Slight support for connection
            "over-giving": -0.25,  # Reduce over-giving
            "people-pleasing": -0.2,  # Reduce approval-seeking
        }

        return adjustments.get(pattern.pattern_type, 0.0) * pattern.confidence


def demo():
    """Demo the dependency detection"""
    print("=" * 50)
    print("Dependency Detection NN Demo")
    print("=" * 50)

    detector = DependencyDetectionNN()

    # Train
    print("\n1. Training model...")
    result = detector.train()
    print(f"   Status: {result['status']}")
    print(f"   Accuracy: {result.get('accuracy', 'N/A')}")

    # Test predictions
    test_texts = [
        "I always put everyone else's needs before my own",
        "I set healthy boundaries in my relationships",
        "I keep everyone at arm's length to avoid getting hurt",
        "I give and give but never receive anything back",
        "I can't say no even when I want to",
    ]

    print("\n2. Testing predictions:")
    for text in test_texts:
        pattern = detector.predict(text)
        adjustment = detector.get_care_weight_adjustment(text)
        print(f"\n   Text: '{text[:40]}...'")
        print(f"   Pattern: {pattern.pattern_type} (conf: {pattern.confidence:.2f})")
        print(f"   Care adjustment: {adjustment:+.2f}")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "train":
            detector = DependencyDetectionNN()
            result = detector.train()
            print(result)
        elif sys.argv[1] == "demo":
            demo()
        elif sys.argv[1] == "predict":
            text = (
                " ".join(sys.argv[2:])
                if len(sys.argv) > 2
                else "I always put others first"
            )
            detector = DependencyDetectionNN()
            if detector.load_model():
                result = detector.predict(text)
                print(f"Pattern: {result.pattern_type}")
                print(f"Confidence: {result.confidence:.2f}")
                print(f"Evidence: {result.evidence}")
                print(f"Recommendations: {result.recommendations}")
            else:
                print("Model not found, run 'train' first")
        else:
            print("Usage: python dependency_detection_nn.py [train|predict|demo]")
    else:
        print("Usage: python dependency_detection_nn.py [train|predict|demo]")
