"""
Provider Registry — Signature-based model resolution inspired by Nanobot.
Replaces hardcoded provider switches with a registry + signature-based resolution.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class ProviderType(Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"


@dataclass
class ProviderSpec:
    id: str
    name: str
    provider_type: ProviderType
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    model_id: Optional[str] = None
    max_tokens: int = 4096
    timeout_seconds: float = 30.0
    # Signature-based matching
    key_prefixes: List[str] = field(default_factory=list)
    url_patterns: List[str] = field(default_factory=list)
    model_keywords: List[str] = field(default_factory=list)
    # Cost & performance
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    typical_tok_per_sec: float = 50.0
    # Capabilities
    supports_tools: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True

    def matches(self, query: str) -> bool:
        """Check if this provider matches a query string (model name, URL, or key prefix)."""
        q = query.lower()
        for prefix in self.key_prefixes:
            if q.startswith(prefix.lower()):
                return True
        for pattern in self.url_patterns:
            if re.search(pattern, q, re.IGNORECASE):
                return True
        for kw in self.model_keywords:
            if kw.lower() in q:
                return True
        return False


class ProviderRegistry:
    """
    Central registry for all LLM providers.
    Auto-detects available providers based on environment variables.
    """

    def __init__(self):
        self._providers: Dict[str, ProviderSpec] = {}
        self._fallback_chains: Dict[str, List[str]] = {}
        self._register_defaults()
        self._auto_detect()

    def _register_defaults(self):
        defaults = [
            ProviderSpec(
                id="ollama-local",
                name="Ollama (Local M4)",
                provider_type=ProviderType.LOCAL,
                base_url="http://localhost:11434",
                model_id="gemma4:e4b",
                max_tokens=256000,
                url_patterns=[r"localhost:1143[4-6]"],
                model_keywords=["gemma", "qwen", "llama"],
                typical_tok_per_sec=120.0,
                supports_tools=True,
                supports_vision=True,
            ),
            ProviderSpec(
                id="cerebras-free",
                name="Cerebras (Free)",
                provider_type=ProviderType.CLOUD,
                base_url="https://api.cerebras.ai/v1",
                api_key_env="CEREBRAS_API_KEY",
                model_id="llama-3.3-70b",
                max_tokens=8192,
                key_prefixes=["cbrs_", "cerebras"],
                model_keywords=["cerebras"],
                typical_tok_per_sec=450.0,
                supports_tools=True,
            ),
            ProviderSpec(
                id="groq-fast",
                name="Groq (Fast)",
                provider_type=ProviderType.CLOUD,
                base_url="https://api.groq.com/openai/v1",
                api_key_env="GROQ_API_KEY",
                model_id="llama-3.3-70b-versatile",
                max_tokens=32768,
                key_prefixes=["gsk_", "groq"],
                model_keywords=["groq"],
                typical_tok_per_sec=350.0,
                supports_tools=True,
            ),
            ProviderSpec(
                id="openrouter",
                name="OpenRouter",
                provider_type=ProviderType.CLOUD,
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
                model_id="meta-llama/llama-3.3-70b-instruct:free",
                max_tokens=64000,
                key_prefixes=["sk-or-", "openrouter"],
                model_keywords=["openrouter", "deepseek", "claude"],
                supports_tools=True,
            ),
            ProviderSpec(
                id="gemini-flash",
                name="Gemini 2.5 Flash",
                provider_type=ProviderType.CLOUD,
                base_url="https://generativelanguage.googleapis.com",
                api_key_env="GOOGLE_API_KEY",
                model_id="gemini-2.5-flash",
                max_tokens=1000000,
                key_prefixes=["AIza", "google"],
                model_keywords=["gemini"],
                typical_tok_per_sec=200.0,
                supports_tools=True,
                supports_vision=True,
            ),
        ]
        for p in defaults:
            self._providers[p.id] = p

        self._fallback_chains = {
            "ollama-local": ["cerebras-free", "groq-fast", "openrouter"],
            "cerebras-free": ["groq-fast", "openrouter"],
            "groq-fast": ["cerebras-free", "openrouter"],
            "openrouter": ["groq-fast", "cerebras-free"],
            "gemini-flash": ["openrouter", "groq-fast"],
        }

    def _auto_detect(self):
        """Scan environment variables and auto-register providers that have keys."""
        for provider in list(self._providers.values()):
            if provider.api_key_env and os.environ.get(provider.api_key_env):
                provider.supports_streaming = True  # Mark as available

    def register(self, spec: ProviderSpec):
        self._providers[spec.id] = spec

    def resolve(self, query: str) -> Optional[ProviderSpec]:
        """Resolve a provider by query string using signature-based matching."""
        for provider in self._providers.values():
            if provider.matches(query):
                return provider
        return None

    def get(self, provider_id: str) -> Optional[ProviderSpec]:
        return self._providers.get(provider_id)

    def list_available(self) -> List[ProviderSpec]:
        """Return providers that are ready to use (have API keys or are local)."""
        return [
            p for p in self._providers.values()
            if p.provider_type == ProviderType.LOCAL or os.environ.get(p.api_key_env or "")
        ]

    def get_fallback_chain(self, provider_id: str) -> List[ProviderSpec]:
        chain_ids = self._fallback_chains.get(provider_id, [])
        return [self._providers[cid] for cid in chain_ids if cid in self._providers]

    def route_by_task(self, task_type: str) -> Optional[ProviderSpec]:
        """Smart routing: map task type to optimal provider."""
        routing = {
            "coding": ["ollama-local", "openrouter", "groq-fast"],
            "creative": ["ollama-local", "cerebras-free", "groq-fast"],
            "reasoning": ["ollama-local", "openrouter", "gemini-flash"],
            "fast": ["cerebras-free", "groq-fast", "ollama-local"],
            "vision": ["ollama-local", "gemini-flash"],
            "agentic": ["openrouter", "ollama-local"],
        }
        for pid in routing.get(task_type, ["ollama-local"]):
            p = self._providers.get(pid)
            if p and (p.provider_type == ProviderType.LOCAL or os.environ.get(p.api_key_env or "")):
                return p
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "providers": {
                pid: {
                    "name": p.name,
                    "type": p.provider_type.value,
                    "available": p.provider_type == ProviderType.LOCAL or bool(os.environ.get(p.api_key_env or "")),
                    "max_tokens": p.max_tokens,
                    "tok_per_sec": p.typical_tok_per_sec,
                }
                for pid, p in self._providers.items()
            },
            "available_count": len(self.list_available()),
        }


# Singleton
_registry = ProviderRegistry()

def get_registry() -> ProviderRegistry:
    return _registry
