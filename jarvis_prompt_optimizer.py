#!/usr/bin/env python3
"""
JARVIS Prompt Optimizer - DSPy-style self-optimizing prompts
Features:
- Automatic prompt optimization based on feedback
- Multi-shot learning from successful interactions
- Metric tracking for prompt effectiveness
- Bootstrap-based prompt improvement

Run: python jarvis_prompt_optimizer.py demo
"""

import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import os


@dataclass
class PromptExample:
    """Example for few-shot learning"""

    input: str
    output: str
    score: float = 1.0  # Quality score (0-1)
    is_positive: bool = True


@dataclass
class PromptMetrics:
    """Metrics for prompt effectiveness"""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    avg_score: float = 0.0
    score_history: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls


@dataclass
class OptimizedPrompt:
    """Optimized prompt with metrics"""

    name: str
    system_prompt: str
    few_shot_examples: List[PromptExample] = field(default_factory=list)
    metrics: PromptMetrics = field(default_factory=PromptMetrics)
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_optimized: str = field(default_factory=lambda: datetime.now().isoformat())


class PromptOptimizer:
    """
    DSPy-style prompt optimizer with bootstrap and self-improvement
    """

    def __init__(self, model_client: Optional[Callable] = None):
        self.model_client = model_client  # Function that calls LLM
        self.prompts: Dict[str, OptimizedPrompt] = {}
        self.score_history: Dict[str, List[float]] = defaultdict(list)

        # Default prompt templates
        self._init_default_prompts()

    def _init_default_prompts(self):
        """Initialize default prompt templates"""
        default_prompts = {
            "sovereign_assistant": OptimizedPrompt(
                name="sovereign_assistant",
                system_prompt="""You are JARVIS, a sovereign AI assistant.
You are helpful, intelligent, and respect user privacy.
Always prioritize the user's goals while maintaining ethical guidelines.
Be concise but thorough in your responses.""",
                few_shot_examples=[
                    PromptExample(
                        input="Hello",
                        output="Good day, sir. How may I assist you?",
                        score=1.0,
                    ),
                    PromptExample(
                        input="What can you do?",
                        output="I can help with questions, tasks, analysis, and more. What do you need?",
                        score=1.0,
                    ),
                ],
            ),
            "care_validator": OptimizedPrompt(
                name="care_validator",
                system_prompt="""You are a care validation assistant.
Evaluate whether text demonstrates care-centered principles:
- Empathy and understanding
- Respect for autonomy
- Constructive tone
- Emotional safety

Respond with a JSON object containing:
{
  "care_score": 0.0-1.0,
  "strengths": ["..."],
  "areas_for_improvement": ["..."],
  "recommendations": ["..."]
}""",
                few_shot_examples=[
                    PromptExample(
                        input="You're wrong about everything.",
                        output='{"care_score": 0.2, "strengths": [], "areas_for_improvement": ["dismissive", "lacking_empathy"], "recommendations": ["Try to understand before judging"]}',
                        score=0.5,
                    ),
                    PromptExample(
                        input="I understand this is hard. Let's work through it together.",
                        output='{"care_score": 0.95, "strengths": ["empathetic", "supportive", "collaborative"], "areas_for_improvement": [], "recommendations": []}',
                        score=1.0,
                    ),
                ],
            ),
            "memory_summarizer": OptimizedPrompt(
                name="memory_summarizer",
                system_prompt="""You are a memory synthesis assistant.
Given a collection of memories, create a coherent summary that:
- Identifies key themes and patterns
- Extracts important facts and learnings
- Notes emotional significance

Respond with a structured JSON summary.""",
                few_shot_examples=[],
            ),
        }

        for prompt in default_prompts.values():
            self.prompts[prompt.name] = prompt

    def get_prompt(self, name: str) -> Optional[OptimizedPrompt]:
        """Get prompt by name"""
        return self.prompts.get(name)

    def list_prompts(self) -> List[Dict]:
        """List all prompts with metrics"""
        return [
            {
                "name": p.name,
                "version": p.version,
                "metrics": {
                    "total_calls": p.metrics.total_calls,
                    "success_rate": p.metrics.success_rate,
                    "avg_score": p.metrics.avg_score,
                },
                "few_shot_count": len(p.few_shot_examples),
                "created": p.created_at,
                "last_optimized": p.last_optimized,
            }
            for p in self.prompts.values()
        ]

    def add_example(self, prompt_name: str, example: PromptExample):
        """Add a new few-shot example to a prompt"""
        if prompt_name not in self.prompts:
            return

        prompt = self.prompts[prompt_name]
        prompt.few_shot_examples.append(example)

        # Keep only top examples
        if len(prompt.few_shot_examples) > 10:
            prompt.few_shot_examples = sorted(
                prompt.few_shot_examples, key=lambda x: x.score, reverse=True
            )[:10]

    def record_outcome(self, prompt_name: str, success: bool, score: float = None):
        """Record the outcome of using a prompt"""
        if prompt_name not in self.prompts:
            return

        prompt = self.prompts[prompt_name]
        prompt.metrics.total_calls += 1

        if success:
            prompt.metrics.successful_calls += 1
        else:
            prompt.metrics.failed_calls += 1

        if score is not None:
            prompt.metrics.score_history.append(score)
            if len(prompt.metrics.score_history) > 100:
                prompt.metrics.score_history = prompt.metrics.score_history[-100:]
            prompt.metrics.avg_score = sum(prompt.metrics.score_history) / len(
                prompt.metrics.score_history
            )

    def build_prompt(
        self, prompt_name: str, user_message: str
    ) -> Tuple[str, List[Dict]]:
        """
        Build a complete prompt with few-shot examples
        Returns: (full_prompt, messages_for_api)
        """
        if prompt_name not in self.prompts:
            return user_message, [{"role": "user", "content": user_message}]

        prompt = self.prompts[prompt_name]

        # Build messages
        messages = [{"role": "system", "content": prompt.system_prompt}]

        # Add few-shot examples
        for example in prompt.few_shot_examples:
            if example.is_positive:
                messages.append({"role": "user", "content": example.input})
                messages.append({"role": "assistant", "content": example.output})

        # Add current message
        messages.append({"role": "user", "content": user_message})

        # Build full text for non-API use
        full_prompt = prompt.system_prompt + "\n\n"
        if prompt.few_shot_examples:
            full_prompt += "Examples:\n"
            for example in prompt.few_shot_examples:
                full_prompt += f"Input: {example.input}\nOutput: {example.output}\n"
            full_prompt += "\n"
        full_prompt += f"Input: {user_message}\nOutput:"

        return full_prompt, messages

    def optimize_prompt(
        self, prompt_name: str, feedback: str, suggested_improvement: str = None
    ) -> bool:
        """
        Optimize a prompt based on feedback
        This is a simplified version - in production would use LLM to generate improvements
        """
        if prompt_name not in self.prompts:
            return False

        prompt = self.prompts[prompt_name]

        # Simple optimization: extract key improvements from feedback
        improvements = []

        # Look for common improvement patterns
        if "more concise" in feedback.lower():
            improvements.append("Be more concise in responses.")
        if "more detailed" in feedback.lower():
            improvements.append("Provide more detailed explanations.")
        if "empathetic" in feedback.lower():
            improvements.append("Show more empathy in responses.")
        if "clearer" in feedback.lower():
            improvements.append("Use clearer language.")

        if improvements or suggested_improvement:
            # Update system prompt
            current_prompt = prompt.system_prompt

            if improvements:
                current_prompt += "\n\nImportant: " + " ".join(improvements)
            if suggested_improvement:
                current_prompt += f"\n\nImprovement: {suggested_improvement}"

            prompt.system_prompt = current_prompt
            prompt.version += 1
            prompt.last_optimized = datetime.now().isoformat()

            return True

        return False

    def bootstrap_examples(
        self, prompt_name: str, examples: List[Dict], quality_fn: Callable[[str], float]
    ):
        """
        Bootstrap few-shot examples by generating and scoring examples
        examples: List of {"input": "...", "expected": "..."}
        quality_fn: Function to evaluate output quality (0-1)
        """
        if prompt_name not in self.prompts or not self.model_client:
            return

        prompt = self.prompts[prompt_name]

        for example in examples:
            # Generate output
            full_prompt, messages = self.build_prompt(prompt_name, example["input"])

            try:
                # Call LLM (placeholder - would integrate with actual client)
                output = (
                    self.model_client(messages)
                    if self.model_client
                    else example.get("expected", "")
                )

                # Evaluate quality
                score = quality_fn(output)

                # Add as example
                prompt_example = PromptExample(
                    input=example["input"],
                    output=output,
                    score=score,
                    is_positive=score >= 0.7,
                )
                self.add_example(prompt_name, prompt_example)

            except Exception as e:
                print(f"Bootstrap error: {e}")

    def export_prompts(self, filepath: str = None) -> Dict:
        """Export all prompts to JSON"""
        data = {}
        for name, prompt in self.prompts.items():
            data[name] = {
                "system_prompt": prompt.system_prompt,
                "version": prompt.version,
                "metrics": {
                    "total_calls": prompt.metrics.total_calls,
                    "successful_calls": prompt.metrics.successful_calls,
                    "failed_calls": prompt.metrics.failed_calls,
                    "avg_score": prompt.metrics.avg_score,
                },
                "few_shot_examples": [
                    {
                        "input": e.input,
                        "output": e.output,
                        "score": e.score,
                        "is_positive": e.is_positive,
                    }
                    for e in prompt.few_shot_examples
                ],
            }

        if filepath:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

        return data

    def import_prompts(self, filepath: str) -> bool:
        """Import prompts from JSON file"""
        if not os.path.exists(filepath):
            return False

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            for name, prompt_data in data.items():
                examples = []
                for e in prompt_data.get("few_shot_examples", []):
                    examples.append(
                        PromptExample(
                            input=e["input"],
                            output=e["output"],
                            score=e.get("score", 1.0),
                            is_positive=e.get("is_positive", True),
                        )
                    )

                self.prompts[name] = OptimizedPrompt(
                    name=name,
                    system_prompt=prompt_data["system_prompt"],
                    few_shot_examples=examples,
                    version=prompt_data.get("version", 1),
                )

            return True
        except Exception as e:
            print(f"Import error: {e}")
            return False


class PromptOptimizerWithLLM(PromptOptimizer):
    """Enhanced prompt optimizer with actual LLM integration"""

    def __init__(self, llm_client, ollama_base: str = "http://localhost:11434"):
        import httpx

        self.llm_client = llm_client
        self.ollama_base = ollama_base
        self.http_client = httpx.AsyncClient(timeout=30.0)
        super().__init__()

    async def generate_optimization(self, prompt_name: str, feedback: str) -> str:
        """Use LLM to generate prompt improvements"""
        if prompt_name not in self.prompts:
            return ""

        prompt = self.prompts[prompt_name]

        optimization_prompt = f"""Analyze this system prompt and suggest improvements based on feedback:

Current prompt:
{prompt.system_prompt}

Feedback:
{feedback}

Suggest a improved version of the system prompt (keep it under 500 words)."""

        try:
            response = await self.http_client.post(
                f"{self.ollama_base}/api/chat",
                json={
                    "model": "qwen2.5:14b",
                    "messages": [{"role": "user", "content": optimization_prompt}],
                    "stream": False,
                },
            )
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
        except:
            pass

        return ""


def simple_score_fn(output: str) -> float:
    """Simple scoring function based on length and structure"""
    score = 0.5

    # Reward JSON-like structure
    if "{" in output and "}" in output:
        score += 0.1

    # Reward reasonable length
    if 50 < len(output) < 500:
        score += 0.1

    # Reward complete sentences
    if output.count(".") > 2:
        score += 0.1

    return min(score, 1.0)


def demo():
    """Demo the prompt optimizer"""
    print("=" * 50)
    print("JARVIS Prompt Optimizer Demo")
    print("=" * 50)

    optimizer = PromptOptimizer()

    # List prompts
    print("\n1. Available prompts:")
    for p in optimizer.list_prompts():
        print(
            f"   - {p['name']} (v{p['version']}, {p['metrics']['success_rate']:.1%} success)"
        )

    # Build a prompt
    print("\n2. Building prompt with few-shot examples...")
    full_prompt, messages = optimizer.build_prompt(
        "sovereign_assistant", "What's the weather?"
    )
    print(f"   System: {messages[0]['content'][:100]}...")
    print(f"   Messages: {len(messages)}")

    # Record outcomes
    print("\n3. Recording outcomes...")
    optimizer.record_outcome("sovereign_assistant", True, 0.9)
    optimizer.record_outcome("sovereign_assistant", True, 0.8)
    optimizer.record_outcome("sovereign_assistant", False, 0.3)

    # Add example
    print("\n4. Adding new example...")
    optimizer.add_example(
        "sovereign_assistant",
        PromptExample(
            input="I'm sad today",
            output="I'm sorry to hear that. Would you like to talk about what's on your mind?",
            score=0.95,
        ),
    )

    # Optimize
    print("\n5. Optimizing prompt...")
    success = optimizer.optimize_prompt(
        "sovereign_assistant", "Make it more empathetic"
    )
    print(f"   Optimization: {'success' if success else 'no change'}")

    # Show metrics
    print("\n6. Final metrics:")
    prompt = optimizer.get_prompt("sovereign_assistant")
    print(f"   Version: {prompt.version}")
    print(f"   Calls: {prompt.metrics.total_calls}")
    print(f"   Avg score: {prompt.metrics.avg_score:.2f}")
    print(f"   Examples: {len(prompt.few_shot_examples)}")

    # Export
    print("\n7. Exporting prompts...")
    optimizer.export_prompts("/tmp/prompts_export.json")
    print("   Exported to /tmp/prompts_export.json")

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        print("Usage: python jarvis_prompt_optimizer.py demo")
