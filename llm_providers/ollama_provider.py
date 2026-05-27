"""
Local LLM provider via Ollama — Llama, Gemma, Nemotron, etc.
Zero cost, full privacy, always available.
"""

import httpx
import logging

logger = logging.getLogger(__name__)


class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def list_models(self) -> list:
        """List all available local models."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.json().get("models", [])
        except Exception as e:
            logger.warning(f"Ollama list_models failed: {e}")
            return []

    async def chat(
        self,
        model: str = "llama3.1:8b",
        messages: list = None,
        system: str = None,
        stream: bool = False,
    ) -> str:
        """Chat completion with a local model."""
        payload = {
            "model": model,
            "messages": messages or [],
            "stream": stream,
        }
        if system:
            payload["messages"].insert(0, {"role": "system", "content": system})

        response = await self.client.post(
            f"{self.base_url}/api/chat", json=payload
        )
        result = response.json()
        return result.get("message", {}).get("content", "")

    async def embed(self, text: str, model: str = "bge-m3") -> list:
        """Generate embeddings locally for memory storage."""
        response = await self.client.post(
            f"{self.base_url}/api/embed",
            json={"model": model, "input": text},
        )
        data = response.json()
        return data.get("embeddings", [[]])[0]

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False


ollama = OllamaProvider()
