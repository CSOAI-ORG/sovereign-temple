"""
MEOK Sovereign Temple — Unified LLM Router

Routes requests to the best available LLM based on task type.
Fallback chain: if primary fails, try local Ollama.
"""

import logging
from .ollama_provider import ollama
from .openrouter_provider import openrouter
from .cerebras_provider import cerebras

logger = logging.getLogger(__name__)


class LLMRouter:
    """Routes requests to the best available LLM based on task type."""

    ROUTES = {
        "quick": {"provider": "ollama", "model": "llama3.1:8b"},
        "private": {"provider": "ollama", "model": "llama3.1:8b"},
        "reasoning": {"provider": "openrouter", "model": "deepseek/deepseek-reasoner"},
        "creative": {"provider": "openrouter", "model": "google/gemini-2.5-flash-preview:thinking"},
        "code": {"provider": "openrouter", "model": "deepseek/deepseek-coder"},
        "fast": {"provider": "cerebras", "model": "llama3.1-70b"},
        "research": {"provider": "openrouter", "model": "google/gemini-2.5-pro"},
        "memory_extraction": {"provider": "ollama", "model": "llama3.1:8b"},
        "care_validation": {"provider": "ollama", "model": "llama3.1:8b"},
        "free": {"provider": "cerebras", "model": "llama3.1-8b"},
        "genesis": {"provider": "openrouter", "model": "deepseek/deepseek-reasoner"},
        "simulation": {"provider": "ollama", "model": "llama3.1:70b"},
        "robotics": {"provider": "openrouter", "model": "deepseek/deepseek-coder"},
    }

    def __init__(self):
        self.providers = {
            "ollama": ollama,
            "openrouter": openrouter,
            "cerebras": cerebras,
        }

    def classify_intent(self, message: str) -> str:
        """Simple intent classification for routing."""
        lower = message.lower()
        if any(w in lower for w in ["code", "debug", "function", "error", "bug", "script"]):
            return "code"
        if any(w in lower for w in ["write", "story", "poem", "creative", "imagine"]):
            return "creative"
        if any(w in lower for w in ["search", "find", "latest", "news", "research"]):
            return "research"
        if any(w in lower for w in ["private", "personal", "diary", "journal", "secret"]):
            return "private"
        if any(w in lower for w in ["quick", "what is", "define", "simple", "yes", "no"]):
            return "quick"
        if any(w in lower for w in ["analyze", "reason", "think", "explain why", "strategy"]):
            return "reasoning"
        if any(w in lower for w in ["genesis", "simulate", "physics", "3d", "robot", "design", "fabricate"]):
            return "genesis"
        if any(w in lower for w in ["gcode", "print", "manufacture", "toolpath", "cnc"]):
            return "robotics"
        return "fast"

    async def route(
        self,
        message: str,
        messages: list = None,
        system: str = None,
        intent: str = None,
    ) -> dict:
        """Route a message to the best provider."""
        if not intent:
            intent = self.classify_intent(message)

        route_config = self.ROUTES.get(intent, self.ROUTES["fast"])
        provider = self.providers[route_config["provider"]]
        model = route_config["model"]

        try:
            response = await provider.chat(
                model=model,
                messages=messages or [{"role": "user", "content": message}],
                system=system,
            )
            return {
                "content": response,
                "provider": route_config["provider"],
                "model": model,
                "intent": intent,
            }
        except Exception as e:
            logger.warning(f"Primary provider failed ({route_config['provider']}): {e}")
            # Fallback: try Ollama local
            if route_config["provider"] != "ollama":
                try:
                    response = await ollama.chat(
                        model="llama3.1:8b",
                        messages=messages or [{"role": "user", "content": message}],
                        system=system,
                    )
                    return {
                        "content": response,
                        "provider": "ollama",
                        "model": "llama3.1:8b",
                        "intent": intent,
                        "fallback": True,
                    }
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")
            return {"error": str(e), "intent": intent}

    async def health(self) -> dict:
        """Check all provider statuses."""
        return {
            "ollama": await ollama.health_check(),
            "openrouter": await openrouter.health_check(),
            "cerebras": await cerebras.health_check(),
        }


router = LLMRouter()
