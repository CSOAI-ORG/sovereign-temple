"""
Kimi Agent Connector — Moonshot AI integration for Sovereign Temple.

Kimi (Moonshot AI) is an OpenAI-compatible LLM with strong code generation
capabilities. This connector lets Sovereign delegate frontend builds,
code reviews, and general tasks to Kimi via API.

API: https://api.moonshot.cn/v1 (OpenAI-compatible)
Models: moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


KIMI_MODELS = {
    "8k": "moonshot-v1-8k",
    "32k": "moonshot-v1-32k",
    "128k": "moonshot-v1-128k",
}

DEFAULT_MODEL = "moonshot-v1-32k"


class KimiAgent:
    """Sovereign-integrated Kimi code agent.

    Wraps Moonshot AI's OpenAI-compatible API for task delegation.
    Tracks task history for performance scoring within Sovereign's
    agent registry.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.moonshot.cn/v1",
        default_model: str = DEFAULT_MODEL,
        timeout: float = 120.0,
    ):
        self.api_key = api_key or os.environ.get("KIMI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

        if not HAS_HTTPX:
            raise RuntimeError("httpx required for Kimi agent")

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

        # Task tracking
        self.task_history: List[Dict[str, Any]] = []
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_tokens_used = 0
        self.created_at = datetime.now().isoformat()

    async def send_task(
        self,
        task_description: str,
        context: str = "",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a general task to Kimi.

        Args:
            task_description: What to do.
            context: Additional context (code, specs, etc.).
            model: Model override (8k/32k/128k or full name).
            temperature: Creativity (0-1).
            max_tokens: Max response length.
            system_prompt: Custom system prompt.

        Returns:
            Dict with response, model, tokens, duration.
        """
        model = KIMI_MODELS.get(model, model) or self.default_model

        if system_prompt is None:
            system_prompt = (
                "You are Kimi, a code agent integrated into the Sovereign Temple system. "
                "You excel at frontend development (React, TypeScript, Next.js), "
                "code generation, code review, and technical analysis. "
                "Be precise, production-ready, and care-aligned."
            )

        messages = [{"role": "system", "content": system_prompt}]

        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})

        messages.append({"role": "user", "content": task_description})

        start = time.time()
        task_record = {
            "task": task_description[:200],
            "model": model,
            "started_at": datetime.now().isoformat(),
            "status": "running",
        }

        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            duration = round(time.time() - start, 2)

            self.tasks_completed += 1
            self.total_tokens_used += usage.get("total_tokens", 0)

            task_record.update({
                "status": "completed",
                "duration_s": duration,
                "tokens": usage.get("total_tokens", 0),
                "response_length": len(content),
            })
            self.task_history.append(task_record)
            self._trim_history()

            return {
                "response": content,
                "model": model,
                "tokens": usage,
                "duration_s": duration,
                "status": "completed",
            }

        except httpx.HTTPStatusError as e:
            self.tasks_failed += 1
            task_record.update({
                "status": "failed",
                "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}",
            })
            self.task_history.append(task_record)
            self._trim_history()
            return {
                "error": f"Kimi API error: {e.response.status_code}",
                "detail": e.response.text[:500],
                "status": "failed",
            }

        except Exception as e:
            self.tasks_failed += 1
            task_record.update({"status": "failed", "error": str(e)})
            self.task_history.append(task_record)
            self._trim_history()
            return {"error": str(e), "status": "failed"}

    async def build_frontend(
        self,
        spec: str,
        framework: str = "Next.js + TypeScript",
        files: Optional[Dict[str, str]] = None,
        model: str = "moonshot-v1-128k",
    ) -> Dict[str, Any]:
        """Specialized frontend build task.

        Args:
            spec: What to build (component, page, feature).
            framework: Target framework.
            files: Existing files as {filename: content} for context.
            model: Defaults to 128k for large codebases.

        Returns:
            Dict with generated code and metadata.
        """
        context_parts = [f"Framework: {framework}"]
        if files:
            for fname, content in files.items():
                context_parts.append(f"--- {fname} ---\n{content}")

        context = "\n\n".join(context_parts)

        system_prompt = (
            f"You are a senior frontend engineer specializing in {framework}. "
            "Generate production-ready, type-safe code. "
            "Include proper error handling, accessibility, and responsive design. "
            "Output complete files with imports."
        )

        result = await self.send_task(
            task_description=f"Build the following:\n\n{spec}",
            context=context,
            model=model,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=8192,
        )

        if result.get("status") == "completed":
            result["task_type"] = "frontend_build"
            result["framework"] = framework

        return result

    async def review_code(
        self,
        code: str,
        language: str = "typescript",
        focus: str = "bugs, performance, accessibility",
    ) -> Dict[str, Any]:
        """Code review via Kimi.

        Args:
            code: Code to review.
            language: Programming language.
            focus: What to focus review on.

        Returns:
            Dict with review findings and suggestions.
        """
        system_prompt = (
            f"You are a senior code reviewer specializing in {language}. "
            f"Focus on: {focus}. "
            "Be specific — cite line numbers, suggest fixes, rate severity. "
            "Format as: ## Issues (critical/warning/info), ## Suggestions, ## Score (1-10)."
        )

        return await self.send_task(
            task_description=f"Review this {language} code:\n\n```{language}\n{code}\n```",
            model="moonshot-v1-32k",
            system_prompt=system_prompt,
            temperature=0.2,
        )

    async def list_models(self) -> Dict[str, Any]:
        """List available Kimi models."""
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            data = response.json()
            return {
                "models": [m["id"] for m in data.get("data", [])],
                "status": "connected",
            }
        except Exception as e:
            return {
                "models": list(KIMI_MODELS.values()),
                "status": "cached_list",
                "error": str(e),
            }

    def get_status(self) -> Dict[str, Any]:
        """Get agent status for MCP."""
        total = self.tasks_completed + self.tasks_failed
        return {
            "agent": "Kimi (Moonshot AI)",
            "available": bool(self.api_key),
            "default_model": self.default_model,
            "models": list(KIMI_MODELS.values()),
            "base_url": self.base_url,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "success_rate": round(
                self.tasks_completed / max(1, total), 3
            ),
            "total_tokens_used": self.total_tokens_used,
            "created_at": self.created_at,
            "recent_tasks": self.task_history[-5:],
        }

    def _trim_history(self, max_size: int = 100):
        if len(self.task_history) > max_size:
            self.task_history = self.task_history[-50:]

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
