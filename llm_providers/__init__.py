"""
MEOK Sovereign Temple — LLM Provider Router

Routes requests to the best available LLM:
  - Ollama (local): Llama 3.1, Gemma3, Nemotron — fast, private, always available
  - Cerebras (cloud free): 1M tokens/day free, ultra-fast Llama 70B
  - OpenRouter (cloud): Claude, GPT, Gemini, DeepSeek — complex reasoning
  - NVIDIA NIM (cloud): Nemotron nano/super/ultra — deep reasoning
"""

from .router import router, LLMRouter

__all__ = ['router', 'LLMRouter']
