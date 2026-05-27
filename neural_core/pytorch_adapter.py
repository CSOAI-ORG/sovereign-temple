"""
PyTorch Model Adapter for Sovereign Temple Neural Core
Wraps GPU-trained .pt models into the BaseNeuralModel interface for CPU inference.

Models trained on Vast.ai (RTX A5000) with PyTorch 2.2.0 / CUDA 12.1
"""

import numpy as np
import os
import json
from typing import Dict, Any, Optional, Type
from datetime import datetime

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from .base_model import BaseNeuralModel


# ---------------------------------------------------------------------------
# PyTorch model architecture classes (must match training pipeline on Vast.ai)
# ---------------------------------------------------------------------------

if TORCH_AVAILABLE:

    class ThreatDetectionNet(nn.Module):
        """Threat classification: 64 -> 256 -> 128 -> 64 -> 5 classes"""

        def __init__(self, input_dim: int = 64, num_classes: int = 5):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 256),
                nn.ReLU(),
                nn.BatchNorm1d(256),
                nn.Dropout(0.3),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.BatchNorm1d(128),
                nn.Dropout(0.2),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, num_classes),
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.net(x)

    class CareValidationNet(nn.Module):
        """Care validation (binary): 32 -> 128 -> 64 -> 1 (sigmoid)"""

        def __init__(self, input_dim: int = 32):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.ReLU(),
                nn.BatchNorm1d(128),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
                nn.Sigmoid(),
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.net(x)

    class PartnershipDetectionNet(nn.Module):
        """Partnership detection (binary): 48 -> 128 -> 64 -> 1 (sigmoid)"""

        def __init__(self, input_dim: int = 48):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.ReLU(),
                nn.BatchNorm1d(128),
                nn.Dropout(0.3),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, 1),
                nn.Sigmoid(),
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.net(x)


# ---------------------------------------------------------------------------
# Generic PyTorch adapter that conforms to BaseNeuralModel
# ---------------------------------------------------------------------------

class PyTorchModelAdapter(BaseNeuralModel):
    """
    Wraps a GPU-trained PyTorch .pt checkpoint into the BaseNeuralModel
    interface so it can be used alongside the existing sklearn models.

    All inference runs on CPU (no GPU required on Mac).
    """

    def __init__(
        self,
        model_name: str,
        model_dir: str = "models",
        model_class: Optional[Type] = None,
        input_dim: int = 64,
    ):
        super().__init__(model_name, model_dir)

        if not TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch is not installed. Install with: pip install torch"
            )

        self.model_class = model_class
        self.input_dim = input_dim
        self.device = torch.device("cpu")

        # Override path to use .pt extension
        self.model_path = os.path.join(model_dir, f"{model_name}.pt")

        # Try to load on init
        self.load_model()

    # -- BaseNeuralModel interface ------------------------------------------

    def extract_features(self, input_data: Any) -> np.ndarray:
        """Convert arbitrary input to a numpy feature vector.

        Accepts:
            - np.ndarray (returned as-is, reshaped if needed)
            - list / tuple of numbers
            - dict with numeric values (sorted by key)
            - raw string (hashed to fixed-dim vector as fallback)
        """
        if isinstance(input_data, np.ndarray):
            vec = input_data.flatten()
        elif isinstance(input_data, (list, tuple)):
            vec = np.array(input_data, dtype=np.float32)
        elif isinstance(input_data, dict):
            vec = np.array(
                [float(v) for _, v in sorted(input_data.items())],
                dtype=np.float32,
            )
        elif isinstance(input_data, str):
            # Deterministic hash-based embedding as fallback
            vec = self._text_to_features(input_data)
        else:
            raise ValueError(f"Unsupported input type: {type(input_data)}")

        # Pad or truncate to expected input_dim
        if len(vec) < self.input_dim:
            vec = np.pad(vec, (0, self.input_dim - len(vec)))
        elif len(vec) > self.input_dim:
            vec = vec[: self.input_dim]

        return vec.astype(np.float32)

    def predict(self, input_data: Any) -> Dict[str, Any]:
        """Run inference on CPU using the loaded PyTorch model."""
        if self.model is None:
            return {"error": f"Model '{self.model_name}' not loaded"}

        features = self.extract_features(input_data)
        tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)

        self.model.eval()
        with torch.no_grad():
            output = self.model(tensor)

        raw = output.squeeze(0).cpu().numpy()

        # Interpret output based on shape
        if raw.shape[0] == 1:
            # Binary (sigmoid output)
            score = float(raw[0])
            return {
                "score": round(score, 4),
                "label": bool(score >= 0.5),
                "confidence": round(abs(score - 0.5) * 2, 4),
                "model": self.model_name,
            }
        else:
            # Multi-class (logits -> softmax)
            probs = torch.softmax(torch.tensor(raw), dim=0).numpy()
            predicted_class = int(np.argmax(probs))
            return {
                "predicted_class": predicted_class,
                "probabilities": {
                    str(i): round(float(p), 4) for i, p in enumerate(probs)
                },
                "confidence": round(float(probs[predicted_class]), 4),
                "model": self.model_name,
            }

    def train_model(self, training_data: Optional[Any] = None) -> Dict[str, float]:
        """Training is done on GPU (Vast.ai). Local ingestion not supported yet."""
        # Graceful fallback: return current metrics so continual learning pipeline
        # doesn't crash on GPU-trained models.
        return self.metrics or {"mse": None, "mae": None, "trained_at": None, "training_samples": 0}

    # -- Load / save overrides for .pt files --------------------------------

    def load_model(self) -> bool:
        """Load a .pt checkpoint with map_location='cpu'."""
        try:
            if not os.path.exists(self.model_path):
                print(f"[PyTorchAdapter] No checkpoint found at {self.model_path}")
                return False

            if self.model_class is None:
                print(f"[PyTorchAdapter] No model_class set for {self.model_name}")
                return False

            # Instantiate architecture then load state dict
            self.model = self.model_class(input_dim=self.input_dim)
            state = torch.load(self.model_path, map_location="cpu", weights_only=True)

            # Support both raw state_dict and wrapped checkpoint
            if isinstance(state, dict) and "model_state_dict" in state:
                self.model.load_state_dict(state["model_state_dict"])
                if "metrics" in state:
                    self.metrics = state["metrics"]
            else:
                self.model.load_state_dict(state)

            self.model.to(self.device)
            self.model.eval()
            self.is_trained = True

            # Load metadata sidecar if present
            meta_path = os.path.join(
                self.model_dir, f"{self.model_name}_metadata.json"
            )
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                    self.metrics = meta.get("metrics", self.metrics)

            print(f"[PyTorchAdapter] Loaded {self.model_name} from {self.model_path}")
            return True

        except Exception as e:
            print(f"[PyTorchAdapter] Error loading {self.model_name}: {e}")
            self.model = None
            self.is_trained = False
            return False

    def save_model(self) -> bool:
        """Save model state dict to .pt file."""
        try:
            if self.model is None:
                return False
            torch.save(self.model.state_dict(), self.model_path)

            meta = {
                "model_name": self.model_name,
                "metrics": self.metrics,
                "is_trained": self.is_trained,
                "backend": "pytorch",
                "input_dim": self.input_dim,
                "saved_at": datetime.now().isoformat(),
            }
            meta_path = os.path.join(
                self.model_dir, f"{self.model_name}_metadata.json"
            )
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)

            return True
        except Exception as e:
            print(f"[PyTorchAdapter] Error saving {self.model_name}: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Extended info including PyTorch-specific details."""
        info = super().get_model_info()
        info.update({
            "backend": "pytorch",
            "input_dim": self.input_dim,
            "device": str(self.device),
            "torch_available": TORCH_AVAILABLE,
        })
        if self.model is not None:
            param_count = sum(p.numel() for p in self.model.parameters())
            info["parameter_count"] = param_count
        return info

    # -- Helpers ------------------------------------------------------------

    def _text_to_features(self, text: str) -> np.ndarray:
        """Deterministic hash-based feature extraction for text input."""
        import hashlib

        vec = np.zeros(self.input_dim, dtype=np.float32)
        words = text.lower().split()
        for i, word in enumerate(words):
            h = int(hashlib.sha256(word.encode()).hexdigest(), 16)
            idx = h % self.input_dim
            vec[idx] += 1.0
        # Normalise
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec


# ---------------------------------------------------------------------------
# Convenience factory functions
# ---------------------------------------------------------------------------

def create_threat_detection_pt(model_dir: str = "models") -> PyTorchModelAdapter:
    """Create a PyTorch-backed threat detection model."""
    return PyTorchModelAdapter(
        model_name="threat_detection",
        model_dir=model_dir,
        model_class=ThreatDetectionNet if TORCH_AVAILABLE else None,
        input_dim=64,
    )


def create_care_validation_pt(model_dir: str = "models") -> PyTorchModelAdapter:
    """Create a PyTorch-backed care validation model."""
    return PyTorchModelAdapter(
        model_name="care_detection",
        model_dir=model_dir,
        model_class=CareValidationNet if TORCH_AVAILABLE else None,
        input_dim=32,
    )


def create_partnership_detection_pt(model_dir: str = "models") -> PyTorchModelAdapter:
    """Create a PyTorch-backed partnership detection model."""
    return PyTorchModelAdapter(
        model_name="partnership_detection",
        model_dir=model_dir,
        model_class=PartnershipDetectionNet if TORCH_AVAILABLE else None,
        input_dim=48,
    )
