#!/usr/bin/env python3
"""
JARVIS Multi-Provider LLM Orchestrator
Seamlessly switches between Ollama, Claude, OpenAI, Gemini
"""

import os
import json
import httpx
from typing import Optional, Dict, Any
from enum import Enum


class LLMProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class JARVISLLM:
    """Multi-provider LLM with automatic fallback"""

    def __init__(self):
        self.providers = []
        self._init_providers()

    def _init_providers(self):
        # Ollama (local)
        if self._check_ollama():
            self.providers.append(("ollama", self._ollama_generate))

        # OpenAI (cloud)
        if os.getenv("OPENAI_API_KEY"):
            self.providers.append(("openai", self._openai_generate))

        # Anthropic Claude (cloud)
        if os.getenv("ANTHROPIC_API_KEY"):
            self.providers.append(("anthropic", self._anthropic_generate))

        # Google Gemini (cloud)
        if os.getenv("GOOGLE_API_KEY"):
            self.providers.append(("google", self._google_generate))

        print(f"🤖 JARVIS LLM initialized with {len(self.providers)} providers")

    def _check_ollama(self) -> bool:
        try:
            r = httpx.get("http://localhost:11434/api/tags", timeout=3)
            return r.status_code == 200
        except:
            return False

    def generate(self, prompt: str, system: str = "", max_tokens: int = 500) -> str:
        """Try each provider in order until one works"""
        last_error = None

        for provider_name, provider_fn in self.providers:
            try:
                result = provider_fn(prompt, system, max_tokens)
                print(f"  ✅ Response from {provider_name}")
                return result
            except Exception as e:
                last_error = e
                print(f"  ⚠️ {provider_name} failed: {e}")
                continue

        return f"I apologize, all AI providers are currently unavailable. Last error: {last_error}"

    def _ollama_generate(self, prompt: str, system: str, max_tokens: int) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        r = httpx.post(
            "http://localhost:11434/api/generate",
            json={"model": "jarvis:latest", "prompt": full_prompt, "stream": False},
            timeout=60,
        )
        return r.json().get("response", "")[:max_tokens]

    def _openai_generate(self, prompt: str, system: str, max_tokens: int) -> str:
        import openai

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _anthropic_generate(self, prompt: str, system: str, max_tokens: int) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _google_generate(self, prompt: str, system: str, max_tokens: int) -> str:
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"{system}\n\n{prompt}" if system else prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        return response.text


# Singleton
jarvis_llm = JARVISLLM()


def chat_with_jarvis(message: str, context: str = "") -> str:
    """Main entry point for JARVIS chat"""
    system = f"""You are JARVIS, an advanced AI assistant.
You have a warm, intelligent personality with a slight wit.
Current context: {context}

Respond naturally, concisely, and helpfully."""

    return jarvis_llm.generate(message, system)


if __name__ == "__main__":
    print("Testing JARVIS with multiple providers...")
    response = chat_with_jarvis("Hello, how are you?")
    print(f"\nJARVIS: {response}")
