#!/usr/bin/env python3
"""
generate_generals.py

Discovers installed Ollama models and auto-generates General configuration entries
in config/generals.yaml. Appends only missing entries, never duplicates.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any

import yaml

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "generals.yaml"


# ── Role detection patterns ───────────────────────────────────────────────────
ROLE_PATTERNS: Dict[str, List[str]] = {
    "embed": ["embed"],
    "coder": ["coder", "code"],
    "vision": ["vision", "vl", "gemma4"],
    "reasoning": ["reason", "r1", "deepseek-r", "think", "qwen3", "nemotron"],
}

ROLE_CAPABILITIES: Dict[str, List[str]] = {
    "coder": ["chat", "code", "tool_use"],
    "reasoning": ["chat", "reasoning", "analysis"],
    "vision": ["chat", "vision", "multimodal"],
    "fast": ["chat", "fast_response", "streaming"],
    "embed": ["embed", "text_processing"],
}

ROLE_PRIORITY = {
    "embed": 3,
    "fast": 4,
    "vision": 6,
    "coder": 7,
    "reasoning": 8,
}


def humanize_name(model_id: str) -> str:
    """Convert a model ID like 'qwen3:8b' into 'Qwen 3 8B'."""
    base, _, tag = model_id.partition(":")
    # Insert space between letters and numbers, e.g. qwen3 -> qwen 3
    base = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", base)
    # Replace hyphens/underscores with spaces
    base = base.replace("-", " ").replace("_", " ")
    # Title-case each word
    base = " ".join(word.capitalize() for word in base.split())

    if tag and tag != "latest":
        # Parameter-size tags (e.g. 8b, 0.6b, e4b) → uppercase letters
        if any(c.isdigit() for c in tag):
            tag_clean = re.sub(r"[a-zA-Z]+", lambda m: m.group(0).upper(), tag)
        else:
            # Other tags → title-case
            tag_clean = tag.capitalize()
        return f"{base} {tag_clean}"
    return base


def detect_provider(model_id: str) -> str:
    """Determine provider based on model name / URL pattern."""
    if model_id.startswith("openrouter/"):
        return "openrouter"
    return "ollama"


def detect_role(model_id: str) -> str:
    """Auto-assign role based on model name patterns.

    Roles: coder, reasoning, vision, fast, embed
    """
    lower = model_id.lower()

    # 1. Very specific functional roles
    if any(p in lower for p in ROLE_PATTERNS["embed"]):
        return "embed"
    if any(p in lower for p in ROLE_PATTERNS["coder"]):
        return "coder"
    if any(p in lower for p in ROLE_PATTERNS["vision"]):
        return "vision"

    # 2. Fast heuristic: tiny parameter counts
    if ":" in model_id:
        tag = model_id.split(":")[1].lower()
        if any(tag.startswith(x) for x in ("0.", "1b", "1.5b", "2b", "3b")):
            return "fast"

    # 3. Explicit reasoning indicators
    if any(p in lower for p in ROLE_PATTERNS["reasoning"]):
        return "reasoning"

    # 4. Default: general-purpose LLMs are treated as reasoning models
    return "reasoning"


def get_capabilities(role: str) -> List[str]:
    return ROLE_CAPABILITIES.get(role, ROLE_CAPABILITIES["reasoning"])


def get_priority(role: str, model_id: str) -> int:
    base = ROLE_PRIORITY.get(role, 5)
    # Bump priority for larger local models (common tags)
    tag = model_id.split(":")[1].lower() if ":" in model_id else ""
    size_boost = 0
    if any(x in tag for x in ("72b", "70b", "65b", "40b", "32b", "31b", "27b")):
        size_boost = 2
    elif any(x in tag for x in ("14b", "13b", "12b", "9b", "8b", "7b")):
        size_boost = 1
    return min(base + size_boost, 10)


def parse_ollama_list() -> List[Dict[str, Any]]:
    """Run `ollama list` and return a list of model dicts."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running 'ollama list': {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'ollama' command not found. Is Ollama installed?", file=sys.stderr)
        sys.exit(1)

    models = []
    # Skip header line
    for line in result.stdout.strip().splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        model_id = parts[0]
        role = detect_role(model_id)
        models.append({
            "id": model_id,
            "name": humanize_name(model_id),
            "provider": detect_provider(model_id),
            "role": role,
            "capabilities": get_capabilities(role),
            "priority": get_priority(role, model_id),
        })
    return models


def load_existing_generals() -> List[Dict[str, Any]]:
    if not CONFIG_PATH.exists():
        return []
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("generals", [])


def save_generals(generals: List[Dict[str, Any]]) -> None:
    """Write generals.yaml without PyYAML anchors/aliases for readability."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    class NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(
            {"generals": generals},
            f,
            Dumper=NoAliasDumper,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )


def main() -> None:
    discovered = parse_ollama_list()
    existing = load_existing_generals()

    existing_ids = {g["id"] for g in existing}
    new_generals = []

    for model in discovered:
        if model["id"] in existing_ids:
            continue
        new_generals.append(model)
        existing.append(model)

    if new_generals:
        save_generals(existing)

    existed = len(discovered) - len(new_generals)
    print(f"Generated {len(new_generals)} new Generals, {existed} already existed")

    if new_generals:
        print("\nNew entries:")
        for g in new_generals:
            print(f"  - {g['id']:<25} -> role={g['role']}, priority={g['priority']}")


if __name__ == "__main__":
    main()
