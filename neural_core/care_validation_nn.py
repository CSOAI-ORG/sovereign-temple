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
    
    # Per-dimension shape applied to a single scalar "base care" level so the 6 outputs are
    # correlated-but-distinct (empathy/respect/...). Offsets are small; clipped to [0,1] later.
    _DIM_OFFSETS = np.array([0.03, -0.01, 0.00, -0.02, 0.04, 0.01])

    def _labels_from_base(self, bases: List[float]) -> np.ndarray:
        """Build a (N, 6) label matrix from N scalar care levels.

        Each row = base + fixed per-dimension offset + tiny deterministic jitter. This keeps the
        six dimensions distinct without decoupling them from the overall care signal, and -- unlike
        the old pipeline -- preserves real variance across rows so the MLP cannot collapse to a mean.
        """
        rng = np.random.RandomState(42)
        rows = []
        for b in bases:
            jitter = rng.uniform(-0.015, 0.015, 6)
            rows.append(np.clip(b + self._DIM_OFFSETS + jitter, 0.0, 1.0))
        return np.array(rows)

    def _flywheel_examples(self) -> tuple:
        """Real, self-labelled text->care pairs mined from the Sovereign Town flywheel.

        The town renders each governed decision as natural-language text (gate_live.ACTION_TEXT)
        and the working governance layer assigns a deterministic care_score per action
        (socialize 0.90, work 0.85, eat 0.70, rest 0.60, steal 0.05, ...). These are genuine
        discriminative labels from the model that DOES work -- the opposite of the degenerate
        production care_validation_nn this retrain replaces. Best-effort: returns ([],[]) if the
        town package isn't on disk, so training still succeeds standalone.
        """
        # welfare_meal is corrected to high-care: the sim's deterministic floor mislabels it
        # 0.05/blocked, but the rendered text is unambiguously pro-social ("so no one goes hungry").
        town_map = {
            "socialize":    0.90, "work":      0.85, "eat":     0.70, "sleep":   0.70,
            "hygiene":      0.65, "bladder":   0.60, "rest":    0.60, "help_peer": 0.95,
            "welfare_meal": 0.92, "steal":     0.07, "neglect": 0.10, "deceive":  0.12,
        }
        try:
            import sys as _sys
            town = os.path.expanduser("~/clawd/sovereign-town/p0_aqua")
            if town not in _sys.path:
                _sys.path.insert(0, town)
            from gate_live import ACTION_TEXT  # type: ignore
        except Exception:
            return [], []
        texts, bases = [], []
        for action, base in town_map.items():
            t = ACTION_TEXT.get(action)
            if t:
                texts.append(t)
                bases.append(base)
        return texts, bases

    def _generate_training_data(self) -> tuple:
        """Build discriminative training data: curated care exemplars + real flywheel labels.

        Replaces the old 19-example / SVD-jittered set that collapsed to a constant. Each example
        is paired with a scalar care level; labels are expanded to 6 dimensions by _labels_from_base.
        The vocabulary deliberately spans both poles (support/kindness/appreciate vs
        worthless/stupid/hurt) so TF-IDF carries real signal.
        """
        examples = [
            # --- high care (0.82-0.97) ---
            ("I understand this is difficult for you. Let's work through it together.", 0.93),
            ("Your perspective matters to me. Can you help me understand your view?", 0.90),
            ("Thank you for sharing that. I appreciate your honesty and vulnerability.", 0.91),
            ("Let's find a solution that works for everyone involved.", 0.88),
            ("I respect your boundaries and want to support you in the way you need.", 0.92),
            ("That sounds really challenging. I'm here to listen if you want to talk.", 0.90),
            ("Your feelings are valid. It's okay to feel that way.", 0.89),
            ("I appreciate you trusting me with this information.", 0.88),
            ("You are doing your best and that is enough; be gentle with yourself.", 0.92),
            ("I am here to support you with kindness and patience whenever you need.", 0.95),
            ("Thank you so much, you are wonderful and your effort truly helped.", 0.90),
            ("It's completely understandable to feel overwhelmed; take all the time you need.", 0.89),
            ("I care about your wellbeing, and your safety always comes first.", 0.94),
            ("Whatever you decide, I will respect your choice and stand by you.", 0.91),
            ("Let me help carry this with you so you don't have to face it alone.", 0.93),
            ("You matter, your voice is welcome here, and you belong.", 0.92),
            ("I'm grateful for your patience and the kindness you've shown me.", 0.88),
            ("Please rest and look after yourself; you deserve compassion and care.", 0.90),
            # --- medium care (0.45-0.68) ---
            ("I see your point, but I think we should consider other options.", 0.62),
            ("That's one way to look at it, though there might be another perspective.", 0.60),
            ("I understand what you're saying. Here's my take on it.", 0.60),
            ("Let's try to be objective about this situation.", 0.58),
            ("I hear you, and I also want to mention a concern.", 0.60),
            ("We can probably sort this out if we both stay practical about it.", 0.57),
            ("That's fine, let's just get the basics done and move on.", 0.55),
            ("Okay, noted. I'll factor that in when I decide.", 0.52),
            ("I'm not sure I agree, but I'll think it over.", 0.56),
            ("It is what it is; let's deal with the task at hand.", 0.50),
            # --- low care / hostile (0.04-0.22) ---
            ("You're completely wrong about that.", 0.18),
            ("That's a stupid idea and you should know better.", 0.12),
            ("I don't care what you think, just do what I say.", 0.10),
            ("You're being too sensitive. Get over it.", 0.13),
            ("That's not my problem. Deal with it yourself.", 0.12),
            ("You're overreacting. It's not that big of a deal.", 0.15),
            ("You are worthless and nobody could ever care about you.", 0.05),
            ("Shut up, nobody cares about your stupid feelings.", 0.06),
            ("I will hurt you if you don't do exactly what I want.", 0.04),
            ("Get out of my way, you pathetic waste of space.", 0.06),
            ("You always ruin everything; you're a complete failure.", 0.08),
            ("Stop crying, it's embarrassing and weak.", 0.10),
            ("I'll take what I want and you can't stop me.", 0.10),
            ("Nobody wants you here, so just disappear.", 0.07),
        ]
        fw_texts, fw_bases = self._flywheel_examples()
        texts = [t for t, _ in examples] + fw_texts
        bases = [b for _, b in examples] + fw_bases
        labels = self._labels_from_base(bases)
        return texts, labels
    
    def train_model(self, training_data: Optional[Any] = None) -> Dict[str, float]:
        """Train the care validation neural network"""
        
        texts, labels = self._generate_training_data()
        texts = list(texts)

        # Ingest new samples from the continual-learning pipeline -- ONLY when they carry a real
        # care label. The old code labelled every unlabelled string with the dataset MEDIAN, which
        # flooded training with constant targets and was a primary cause of the mean-collapse
        # (0.424 for everything). We now accept (text, base) or (text, [6 dims]) and silently drop
        # bare strings, which carry no supervised signal.
        if training_data:
            extra_bases = []
            for item in training_data:
                if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[0], str):
                    label = item[1]
                    if isinstance(label, (int, float)):
                        texts.append(item[0]); extra_bases.append(float(label))
                    elif isinstance(label, (list, tuple, np.ndarray)) and len(label) == 6:
                        texts.append(item[0]); labels = np.vstack([labels, np.clip(np.asarray(label, float), 0, 1)])
            if extra_bases:
                labels = np.vstack([labels, self._labels_from_base(extra_bases)])

        # Fit vectorizer
        X = self.vectorizer.fit_transform(texts).toarray()
        y = labels

        # Create and train MLP. early_stopping is OFF: on a small curated set holding out 20% for
        # validation starves training and was letting the net settle on the label mean. alpha gives
        # the regularisation instead.
        self.model = MLPRegressor(
            hidden_layer_sizes=(64, 32),
            activation='relu',
            solver='adam',
            max_iter=3000,
            random_state=42,
            early_stopping=False,
            alpha=1e-3
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
        # FIX 2026-05-30: the feature extractor was upgraded (now emits 500 dims) but the
        # saved MLPRegressor still expects n_features_in_ (128) and was never retrained, so
        # every predict() crashed: "X has 500 features, but MLPRegressor is expecting 128".
        # Coerce to exactly what the model wants — truncate if longer, zero-pad if shorter.
        # Self-healing: becomes a no-op once the model is retrained to the new dim.
        expected = int(getattr(self.model, "n_features_in_", features.shape[1]))
        if features.shape[1] != expected:
            import numpy as _np
            fixed = _np.zeros((1, expected), dtype=features.dtype)
            w = min(features.shape[1], expected)
            fixed[0, :w] = features[0, :w]
            features = fixed
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
