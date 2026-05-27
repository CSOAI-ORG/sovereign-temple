#!/usr/bin/env python3
"""
Model Gateway - Unified Multi-Model Router
Routes requests to appropriate models based on task, cost, latency
Supports: Ollama, OpenRouter, OpenAI, Anthropic, vLLM
"""

import os
import json
import time
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import httpx


class TaskType(Enum):
    """Task classification for routing"""

    CONVERSATIONAL = "conversational"
    ANALYTICAL = "analytical"
    CODING = "coding"
    REASONING = "reasoning"
    VISION = "vision"
    CREATIVE = "creative"
    TOOL_USE = "tool_use"
    FAST_RESPONSE = "fast_response"


@dataclass
class ModelConfig:
    """Configuration for a model endpoint"""

    name: str
    endpoint: str
    api_key: Optional[str] = None
    provider: str = "ollama"  # ollama, openrouter, openai, anthropic
    max_tokens: int = 4096
    context_window: int = 32768
    latency_tier: str = "fast"  # fast, medium, slow
    cost_tier: str = "low"  # low, medium, high
    strengths: List[str] = field(default_factory=list)
    vision_capable: bool = False
    tool_use_capable: bool = False
    enabled: bool = True


@dataclass
class ModelResponse:
    """Standardized response from any model"""

    content: str
    model: str
    latency_ms: float
    tokens_used: int = 0
    finish_reason: str = "stop"
    error: Optional[str] = None


class ModelGateway:
    """
    Unified model gateway - routes to best model for task
    Features: fallback chain, cost optimization, latency routing
    """

    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self.default_models: Dict[TaskType, List[str]] = {}
        self._initialize_models()

    def _initialize_models(self):
        """Initialize configured models"""

        # Primary: Gemma 4 on Vast.ai
        self.register_model(
            ModelConfig(
                name="gemma4:31b",
                endpoint="http://localhost:11436/api/chat",  # SSH tunnel
                provider="ollama",
                latency_tier="medium",
                cost_tier="low",
                strengths=["reasoning", "vision", "multimodal", "coding"],
                vision_capable=True,
                tool_use_capable=True,
            )
        )

        # Fallback: Local Ollama
        self.register_model(
            ModelConfig(
                name="qwen2.5:7b",
                endpoint="http://localhost:11434/api/chat",
                provider="ollama",
                max_tokens=2048,
                latency_tier="fast",
                cost_tier="low",
                strengths=["conversational", "fast_response"],
            )
        )

        # Cloud fallbacks via OpenRouter
        self.register_model(
            ModelConfig(
                name="deepseek/deepseek-r1",
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                provider="openrouter",
                max_tokens=4096,
                latency_tier="slow",
                cost_tier="low",
                strengths=["reasoning", "analytical"],
                tool_use_capable=True,
            )
        )

        self.register_model(
            ModelConfig(
                name="qwen/qwen3-coder",
                endpoint="https://openrouter.ai/api/v1/chat/completions",
                api_key=os.getenv("OPENROUTER_API_KEY"),
                provider="openrouter",
                max_tokens=4096,
                latency_tier="medium",
                cost_tier="medium",
                strengths=["coding", "architecture"],
            )
        )

        # Default routing
        self.default_models = {
            TaskType.CONVERSATIONAL: ["gemma4:31b", "qwen2.5:7b"],
            TaskType.ANALYTICAL: ["gemma4:31b", "deepseek/deepseek-r1"],
            TaskType.CODING: ["gemma4:31b", "qwen/qwen3-coder"],
            TaskType.REASONING: ["deepseek/deepseek-r1", "gemma4:31b"],
            TaskType.VISION: ["gemma4:31b"],
            TaskType.CREATIVE: ["gemma4:31b", "qwen2.5:7b"],
            TaskType.TOOL_USE: ["gemma4:31b", "deepseek/deepseek-r1"],
            TaskType.FAST_RESPONSE: ["qwen2.5:7b", "gemma4:31b"],
        }

    def register_model(self, config: ModelConfig):
        """Register a model configuration"""
        self.models[config.name] = config

    def classify_task(self, prompt: str) -> TaskType:
        """Classify task type from prompt"""
        prompt_lower = prompt.lower()

        # Coding detection
        code_keywords = [
            "code",
            "function",
            "class",
            "implement",
            "debug",
            "refactor",
            "api",
        ]
        if any(kw in prompt_lower for kw in code_keywords):
            return TaskType.CODING

        # Vision detection
        vision_keywords = ["image", "picture", "screenshot", "see", "visual", "look at"]
        if any(kw in prompt_lower for kw in vision_keywords):
            return TaskType.VISION

        # Reasoning detection
        reasoning_keywords = [
            "reason",
            "explain",
            "why",
            "how",
            "analyze",
            "compare",
            "think",
        ]
        if any(kw in prompt_lower for kw in reasoning_keywords):
            return TaskType.REASONING

        # Analytical
        analytical_keywords = [
            "calculate",
            "math",
            "data",
            "statistics",
            "metrics",
            "compare",
        ]
        if any(kw in prompt_lower for kw in analytical_keywords):
            return TaskType.ANALYTICAL

        # Creative
        creative_keywords = [
            "write",
            "story",
            "creative",
            "poem",
            "song",
            " imagine",
            "generate",
        ]
        if any(kw in prompt_lower for kw in creative_keywords):
            return TaskType.CREATIVE

        # Tool use
        tool_keywords = ["search", "find", "look up", "get", "fetch", "call", "execute"]
        if any(kw in prompt_lower for kw in tool_keywords):
            return TaskType.TOOL_USE

        # Fast response (short prompts)
        if len(prompt.split()) <= 10:
            return TaskType.FAST_RESPONSE

        return TaskType.CONVERSATIONAL

    def get_model_chain(self, task_type: TaskType) -> List[ModelConfig]:
        """Get model chain for task type (tries in order)"""
        model_names = self.default_models.get(task_type, ["gemma4:31b"])
        chain = []

        for name in model_names:
            if name in self.models and self.models[name].enabled:
                chain.append(self.models[name])

        return chain

    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Dict]] = None,
        task_type: Optional[TaskType] = None,
        model_name: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs,
    ) -> ModelResponse:
        """Generate response - routes to appropriate model with fallback"""

        start_time = time.time()

        # Classify task if not specified
        if task_type is None:
            task_type = self.classify_task(prompt)

        # Build message list
        msg_list = messages or [{"role": "user", "content": prompt}]

        # Use specific model or get chain
        if model_name and model_name in self.models:
            chain = [self.models[model_name]]
        else:
            chain = self.get_model_chain(task_type)

        # Try each model in chain
        last_error = None
        for model in chain:
            try:
                response = await self._call_model(
                    model, msg_list, max_tokens, temperature, **kwargs
                )
                response.latency_ms = (time.time() - start_time) * 1000
                return response
            except Exception as e:
                last_error = str(e)
                continue

        # All failed
        return ModelResponse(
            content=f"All model endpoints failed. Last error: {last_error}",
            model="none",
            latency_ms=(time.time() - start_time) * 1000,
            error=last_error or "No models available",
        )

    async def _call_model(
        self,
        model: ModelConfig,
        messages: List[Dict],
        max_tokens: int,
        temperature: float,
        **kwargs,
    ) -> ModelResponse:
        """Call a specific model"""

        headers = {}
        if model.api_key:
            headers["Authorization"] = f"Bearer {model.api_key}"

        # Build request based on provider
        if model.provider == "ollama":
            payload = {
                "model": model.name,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": min(max_tokens, model.max_tokens),
                },
            }
        elif model.provider == "openrouter":
            payload = {
                "model": model.name,
                "messages": messages,
                "max_tokens": min(max_tokens, model.max_tokens),
                "temperature": temperature,
            }
        else:
            payload = {
                "model": model.name,
                "messages": messages,
                "max_tokens": min(max_tokens, model.max_tokens),
                "temperature": temperature,
            }

        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(model.endpoint, json=payload, headers=headers)
            res.raise_for_status()
            data = res.json()

            # Parse response based on provider
            if model.provider == "ollama":
                content = data.get("message", {}).get("content", "")
                tokens = data.get("eval_count", 0)
            else:
                content = (
                    data.get("choices", [{}])[0].get("message", {}).get("content", "")
                )
                tokens = data.get("usage", {}).get("total_tokens", 0)

            return ModelResponse(
                content=content,
                model=model.name,
                latency_ms=0,
                tokens_used=tokens,
            )

    def get_status(self) -> Dict:
        """Get gateway status"""
        return {
            "models": {
                name: {
                    "enabled": m.enabled,
                    "latency_tier": m.latency_tier,
                    "cost_tier": m.cost_tier,
                    "strengths": m.strengths,
                    "vision": m.vision_capable,
                    "tools": m.tool_use_capable,
                }
                for name, m in self.models.items()
            },
            "task_routes": {
                task.value: [m.name for m in self.get_model_chain(task)]
                for task in TaskType
            },
        }


# Global gateway
_gateway: Optional[ModelGateway] = None


def get_model_gateway() -> ModelGateway:
    global _gateway
    if _gateway is None:
        _gateway = ModelGateway()
    return _gateway


if __name__ == "__main__":
    import asyncio

    async def test():
        gateway = get_model_gateway()

        print("=== Model Gateway Status ===")
        print(json.dumps(gateway.get_status(), indent=2))

        print("\n=== Testing Task Classification ===")
        test_prompts = [
            "Hello, how are you?",
            "Write a function to sort a list",
            "Why is the sky blue?",
            "Look at this image",
            "What's 2+2?",
        ]

        for prompt in test_prompts:
            task = gateway.classify_task(prompt)
            chain = [m.name for m in gateway.get_model_chain(task)]
            print(f"Prompt: {prompt[:30]}... -> {task.value} -> {chain}")

        print("\n=== Testing Generation ===")
        response = await gateway.generate("Hello, what are you?")
        print(f"Response: {response.content[:100]}...")
        print(f"Model: {response.model}, Latency: {response.latency_ms:.0f}ms")

    asyncio.run(test())
