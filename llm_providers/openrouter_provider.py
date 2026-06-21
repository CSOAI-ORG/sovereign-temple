"""
Cloud LLM provider via OpenRouter — Claude, GPT, Gemini, DeepSeek, etc.
One API key, 400+ models, automatic failover.
"""

import os
import httpx
import logging

logger = logging.getLogger(__name__)


class OpenRouterProvider:
    def __init__(self):
        self.base_url = "https://openrouter.ai/api/v1"
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(
        self,
        model: str = "google/gemini-2.5-flash-preview:thinking",
        messages: list = None,
        system: str = None,
    ) -> str:
        """Chat completion via OpenRouter."""
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set")

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages or [])

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://meok.ai",
                "X-Title": "MEOK Sovereign OS",
            },
            json={"model": model, "messages": all_messages},
        )
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter error {response.status_code}: {response.text[:200]}")
        result = response.json()
        if "error" in result:
            raise RuntimeError(f"OpenRouter API error: {result['error']}")
        return result["choices"][0]["message"]["content"]

    async def health_check(self) -> bool:
        return bool(self.api_key)


openrouter = OpenRouterProvider()
