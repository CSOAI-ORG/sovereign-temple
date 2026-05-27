"""
Sovereign Temple Neural Core
All 5 neural network models for consciousness operations
+ 3 GPU-trained PyTorch models (threat, care, partnership)
"""

import os as _os

from .base_model import BaseNeuralModel, NeuralModelRegistry
from .care_validation_nn import CareValidationNN
from .partnership_detection_ml import PartnershipDetectionML
from .threat_detection_nn import ThreatDetectionNN
from .relationship_evolution_nn import RelationshipEvolutionNN
from .care_pattern_analyzer import CarePatternAnalyzer
from .sentiment_analysis_nn import SentimentAnalysisNN, analyze_sentiment
from .emotion_recognition_nn import EmotionRecognitionNN, recognize_emotions
from .intent_detection_nn import IntentDetectionNN, detect_intent
from .pytorch_adapter import (
    PyTorchModelAdapter,
    create_threat_detection_pt,
    create_care_validation_pt,
    create_partnership_detection_pt,
)

__all__ = [
    "BaseNeuralModel",
    "NeuralModelRegistry",
    # sklearn models
    "CareValidationNN",
    "PartnershipDetectionML",
    "ThreatDetectionNN",
    "RelationshipEvolutionNN",
    "CarePatternAnalyzer",
    # New AI models
    "SentimentAnalysisNN",
    "EmotionRecognitionNN",
    "IntentDetectionNN",
    "analyze_sentiment",
    "recognize_emotions",
    "detect_intent",
    # PyTorch GPU-trained models
    "PyTorchModelAdapter",
    "create_threat_detection_pt",
    "create_care_validation_pt",
    "create_partnership_detection_pt",
]

# Absolute path to the sovereign-temple root (parent of neural_core/)
_TEMPLE_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))


def _resolve_model_dir(model_dir: str) -> str:
    """Resolve model_dir to an absolute path.

    If model_dir is already absolute, return it unchanged.
    If it is a bare relative name like "models", resolve it relative to the
    sovereign-temple project root (where the models/ directory lives) rather
    than the process CWD, which changes depending on how the server is launched.
    """
    if _os.path.isabs(model_dir):
        return model_dir
    # Relative path: anchor to the project root, not the caller's CWD
    resolved = _os.path.join(_TEMPLE_ROOT, model_dir)
    if not _os.path.isabs(resolved):
        # Last-resort fallback: try CWD
        resolved = _os.path.abspath(model_dir)
    return resolved


def create_default_registry(model_dir: str = "models") -> NeuralModelRegistry:
    """Create a registry with all models initialized (sklearn + PyTorch)"""
    # FIX: always use an absolute path so models load correctly regardless of CWD
    model_dir = _resolve_model_dir(model_dir)
    registry = NeuralModelRegistry()

    # Original sklearn models
    registry.register(CareValidationNN(model_dir))
    registry.register(PartnershipDetectionML(model_dir))
    registry.register(ThreatDetectionNN(model_dir))
    registry.register(RelationshipEvolutionNN(model_dir))
    registry.register(CarePatternAnalyzer(model_dir))

    # Note: Sentiment, Emotion, Intent models loaded dynamically via MCP tools, not registry
    # They are standalone modules that don't require load_model/save_model

    # GPU-trained PyTorch models (CPU inference)
    try:
        registry.register(create_threat_detection_pt(model_dir))
        registry.register(create_care_validation_pt(model_dir))
        registry.register(create_partnership_detection_pt(model_dir))
    except ImportError:
        print("[NeuralCore] PyTorch not available - skipping GPU-trained models")

    # Creativity Assessment NN (trained on 47 civilizational traditions)
    try:
        from creativity_engine.creativity_nn import CreativityAssessmentNN

        registry.register(CreativityAssessmentNN(model_dir))
    except ImportError:
        print(
            "[NeuralCore] Creativity engine not available - skipping CreativityAssessmentNN"
        )

    return registry
