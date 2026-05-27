"""
Free ultra-fast inference via Cerebras — 1M tokens/day free.
450 tokens/second on Llama 70B.
"""

import os
import httpx
import logging

logger = logging.getLogger(__name__)


class CerebrasProvider:
    def __init__(self):
        self.base_url = "https://api.cerebras.ai/v1"
        self.api_key = os.getenv("CEREBRAS_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def chat(
        self,
        model: str = "llama3.1-70b",
        messages: list = None,
        system: str = None,
    ) -> str:
        """Chat completion via Cerebras free tier."""
        if not self.api_key:
            raise RuntimeError("CEREBRAS_API_KEY not set")

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages or [])

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": model, "messages": all_messages},
        )
        result = response.json()
        return result["choices"][0]["message"]["content"]

    async def health_check(self) -> bool:
        return bool(self.api_key)


cerebras = CerebrasProvider()
