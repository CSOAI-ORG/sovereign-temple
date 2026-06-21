"""Model registry — maps tiers to available models per platform."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ModelCapability(Enum):
    CHAT = "chat"
    CODE = "code"
    REASONING = "reasoning"
    VISION = "vision"
    TOOL_USE = "tool_use"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"


@dataclass
class ModelSpec:
    id: str
    name: str
    params_b: float
    quant: str
    size_mb: int
    capabilities: List[ModelCapability] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)
    format: str = "gguf"  # gguf, mlc, onnx, mlx, tflite
    source_url: str = ""
    fallback_to: Optional[str] = None


class ModelRegistry:
    """Central registry of available models per platform/tier."""

    DEFAULT_MODELS: Dict[str, Dict[str, str]] = {
        "ios": {
            "l1": "gemma-4b-mlx-q4",
            "l2": "qwen-7b-mlx-q4",
            "l3": "openrouter/deepseek-v4",
        },
        "android": {
            "l1": "gemma-4b-mediapipe-q4",
            "l2": "qwen-7b-mediapipe-q4",
            "l3": "openrouter/deepseek-v4",
        },
        "windows": {
            "l1": "phi-3-llamacpp-q4",
            "l2": "qwen-14b-llamacpp-q4",
            "l3": "openrouter/deepseek-v4",
        },
        "macos": {
            "l1": "gemma-4b-mlx-q4",
            "l2": "qwen-14b-mlx-q4",
            "l3": "openrouter/deepseek-v4",
        },
        "web": {
            "l1": "gemma-4b-webllm-q4",
            "l2": "qwen-7b-webllm-q4",
            "l3": "openrouter/deepseek-v4",
        },
        "chrome-ext": {
            "l1": "phi-2-webllm-q4",
            "l2": "gemma-4b-webllm-q4",
            "l3": "openrouter/deepseek-v4",
        },
    }

    MODELS: List[ModelSpec] = [
        # L1: On-device small models
        ModelSpec("gemma-4b-mlx-q4", "Gemma 4B MLX Q4", 4.0, "Q4", 2500,
                  [ModelCapability.CHAT, ModelCapability.SUMMARIZE, ModelCapability.TRANSLATE],
                  ["ios", "macos"], "mlx", "https://huggingface.co/google/gemma-3-4b-it"),
        ModelSpec("gemma-4b-mediapipe-q4", "Gemma 4B MediaPipe Q4", 4.0, "Q4", 2200,
                  [ModelCapability.CHAT, ModelCapability.SUMMARIZE],
                  ["android", "ios"], "tflite", "https://huggingface.co/google/gemma-3-4b-it"),
        ModelSpec("phi-3-llamacpp-q4", "Phi-3 Mini llama.cpp Q4", 3.8, "Q4", 2100,
                  [ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.SUMMARIZE],
                  ["windows", "macos", "linux"], "gguf", "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct"),
        ModelSpec("phi-2-webllm-q4", "Phi-2 WebLLM Q4", 2.7, "Q4", 1600,
                  [ModelCapability.CHAT, ModelCapability.SUMMARIZE],
                  ["web", "chrome-ext"], "mlc", "https://huggingface.co/microsoft/phi-2"),
        ModelSpec("gemma-4b-webllm-q4", "Gemma 4B WebLLM Q4", 4.0, "Q4", 2500,
                  [ModelCapability.CHAT, ModelCapability.SUMMARIZE, ModelCapability.TRANSLATE],
                  ["web", "chrome-ext"], "mlc", "https://huggingface.co/google/gemma-3-4b-it"),

        # L2: Edge/larger local models
        ModelSpec("qwen-7b-mlx-q4", "Qwen 2.5 7B MLX Q4", 7.0, "Q4", 4500,
                  [ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.REASONING, ModelCapability.TOOL_USE],
                  ["ios", "macos"], "mlx", "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct"),
        ModelSpec("qwen-7b-mediapipe-q4", "Qwen 2.5 7B MediaPipe Q4", 7.0, "Q4", 4200,
                  [ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.REASONING],
                  ["android"], "tflite", "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct"),
        ModelSpec("qwen-14b-llamacpp-q4", "Qwen 2.5 14B llama.cpp Q4", 14.0, "Q4", 8500,
                  [ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.REASONING, ModelCapability.TOOL_USE],
                  ["windows", "macos", "linux"], "gguf", "https://huggingface.co/Qwen/Qwen2.5-14B-Instruct"),
        ModelSpec("qwen-7b-webllm-q4", "Qwen 2.5 7B WebLLM Q4", 7.0, "Q4", 4500,
                  [ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.REASONING],
                  ["web"], "mlc", "https://huggingface.co/Qwen/Qwen2.5-7B-Instruct"),

        # L3: Cloud APIs (no local download)
        ModelSpec("openrouter/deepseek-v4", "DeepSeek V4 (Cloud)", 100.0, "FP16", 0,
                  [ModelCapability.CHAT, ModelCapability.CODE, ModelCapability.REASONING, ModelCapability.VISION, ModelCapability.TOOL_USE],
                  ["all"], "api", "https://openrouter.ai/deepseek/deepseek-v4"),
    ]

    def __init__(self):
        self._models = {m.id: m for m in self.MODELS}

    def get(self, model_id: str) -> Optional[ModelSpec]:
        return self._models.get(model_id)

    def get_default_model(self, tier, platform: str = "web") -> str:
        """Get default model for tier + platform."""
        tier_key = tier.value if hasattr(tier, 'value') else str(tier)
        tier_key = tier_key.replace("l0", "l1")  # L0 uses L1 models
        platform_models = self.DEFAULT_MODELS.get(platform, self.DEFAULT_MODELS["web"])
        return platform_models.get(tier_key, platform_models.get("l3", "openrouter/deepseek-v4"))

    def list_for_platform(self, platform: str) -> List[ModelSpec]:
        return [m for m in self.MODELS if platform in m.platforms or "all" in m.platforms]

    def list_for_tier(self, tier, platform: str = "web") -> List[ModelSpec]:
        tier_key = tier.value if hasattr(tier, 'value') else str(tier)
        default = self.get_default_model(tier, platform)
        return [m for m in self.MODELS if m.id == default or (platform in m.platforms and m.format != "api")]
