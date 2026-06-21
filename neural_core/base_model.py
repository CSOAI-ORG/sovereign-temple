"""
Base Neural Network Model for Sovereign Temple
Provides common functionality for all neural models
"""

import numpy as np
import pickle
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import json


class BaseNeuralModel(ABC):
    """Base class for all Sovereign neural network models"""
    
    def __init__(self, model_name: str, model_dir: str = "models"):
        self.model_name = model_name
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, f"{model_name}.pkl")
        self.metadata_path = os.path.join(model_dir, f"{model_name}_metadata.json")
        self.model = None
        self.metrics = {"mse": None, "mae": None, "trained_at": None}
        self.is_trained = False
        
        # Ensure model directory exists
        os.makedirs(model_dir, exist_ok=True)
        
    @abstractmethod
    def extract_features(self, input_data: Any) -> np.ndarray:
        """Extract features from input data - implemented by subclasses"""
        pass
    
    @abstractmethod
    def train_model(self, training_data: Optional[Any] = None) -> Dict[str, float]:
        """Train the model - implemented by subclasses"""
        pass
    
    @abstractmethod
    def predict(self, input_data: Any) -> Dict[str, Any]:
        """Make prediction - implemented by subclasses"""
        pass
    
    def save_model(self) -> bool:
        """Save model to disk"""
        try:
            if self.model is not None:
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self.model, f)
                
                # Save metadata
                metadata = {
                    "model_name": self.model_name,
                    "metrics": self.metrics,
                    "is_trained": self.is_trained,
                    "saved_at": datetime.now().isoformat()
                }
                with open(self.metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                return True
        except Exception as e:
            print(f"Error saving model {self.model_name}: {e}")
        return False
    
    def load_model(self) -> bool:
        """Load model from disk"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)

                # Load metadata
                if os.path.exists(self.metadata_path):
                    with open(self.metadata_path, 'r') as f:
                        metadata = json.load(f)
                        self.metrics = metadata.get("metrics", {})
                        self.is_trained = metadata.get("is_trained", False)
                return True
            else:
                import warnings
                warnings.warn(
                    f"[NeuralModel] WARNING: model file not found at '{self.model_path}'. "
                    f"Model '{self.model_name}' will not produce predictions until trained. "
                    f"Run create_dummy_models.py or allow the server to auto-train on startup.",
                    stacklevel=2,
                )
        except Exception as e:
            print(f"Error loading model {self.model_name}: {e}")
        return False

    def safe_features(self, features: np.ndarray) -> np.ndarray:
        """Sanitize feature array: replace NaN/Inf with 0.0 to prevent silent zero predictions."""
        return np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=0.0)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "is_trained": self.is_trained,
            "metrics": self.metrics,
            "model_exists": os.path.exists(self.model_path),
            "model_size_bytes": os.path.getsize(self.model_path) if os.path.exists(self.model_path) else 0
        }


class NeuralModelRegistry:
    """Registry for managing all neural models"""
    
    def __init__(self):
        self.models: Dict[str, BaseNeuralModel] = {}
    
    def register(self, model: BaseNeuralModel) -> None:
        """Register a model"""
        self.models[model.model_name] = model
    
    def get(self, model_name: str) -> Optional[BaseNeuralModel]:
        """Get a model by name"""
        return self.models.get(model_name)
    
    def list_models(self) -> Dict[str, Dict[str, Any]]:
        """List all registered models with info"""
        return {name: model.get_model_info() for name, model in self.models.items()}
    
    def train_all(self) -> Dict[str, Dict[str, float]]:
        """Train all registered models"""
        results = {}
        for name, model in self.models.items():
            print(f"Training model: {name}")
            results[name] = model.train_model()
            model.save_model()
        return results
    
    def load_all(self) -> Dict[str, bool]:
        """Load all registered models from disk"""
        results = {}
        for name, model in self.models.items():
            results[name] = model.load_model()
        return results
