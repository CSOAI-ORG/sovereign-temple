#!/usr/bin/env python3
"""
Prepare fine-tuning dataset from reflections + memories.
Formats for LoRA training (unsloth/trl).
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, "/Users/nicholas/clawd/sovereign-temple")


def load_reflections():
    conn = sqlite3.connect("/Users/nicholas/clawd/sovereign-temple/data/reflection_store.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT task_type, task_summary, model_used, success FROM reflections WHERE success = 1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_jarvis_conversations():
    path = Path("/Users/nicholas/clawd/jarvis-memory/conversations.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else []


def format_alpaca(task_input: str, task_output: str, task_type: str) -> dict:
    instruction = f"[{task_type.upper()}] {task_input}"
    return {
        "instruction": instruction,
        "input": "",
        "output": task_output,
    }


def format_chatml(system: str, user: str, assistant: str) -> dict:
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ]
    }


def main():
    print("=" * 60)
    print("FINETUNE DATASET PREP")
    print("=" * 60)

    reflections = load_reflections()
    print(f"Loaded {len(reflections)} reflections")

    conversations = load_jarvis_conversations()
    print(f"Loaded {len(conversations)} conversations")

    dataset = []

    # From reflections
    system_prompt = (
        "You are MEOKCLAW, a sovereign AI assistant. "
        "You excel at coding, reasoning, creative tasks, and governance. "
        "Respond with insight, precision, and care."
    )

    for r in reflections:
        text = r["task_summary"]
        if len(text) < 20:
            continue
        hemi = r["task_type"]
        dataset.append(format_chatml(
            system=system_prompt,
            user=text[:200],
            assistant=text[:400],
        ))

    # From conversations (if structured)
    for conv in conversations:
        if isinstance(conv, dict) and "messages" in conv:
            msgs = conv["messages"]
            if len(msgs) >= 2:
                dataset.append({"messages": msgs})
        elif isinstance(conv, dict) and "user" in conv and "assistant" in conv:
            dataset.append(format_chatml(
                system=system_prompt,
                user=conv["user"],
                assistant=conv["assistant"],
            ))

    # Deduplicate by output text
    seen = set()
    unique = []
    for item in dataset:
        key = json.dumps(item["messages"][-1]["content"]) if "messages" in item else json.dumps(item.get("output", ""))
        if key not in seen:
            seen.add(key)
            unique.append(item)

    print(f"Unique examples: {len(unique)}")

    # Split train/valid
    split = int(len(unique) * 0.95)
    train = unique[:split]
    valid = unique[split:]

    out_dir = Path("/Users/nicholas/clawd/sovereign-temple/data/finetune")
    out_dir.mkdir(exist_ok=True)

    with open(out_dir / "train.jsonl", "w") as f:
        for item in train:
            f.write(json.dumps(item) + "\n")

    with open(out_dir / "valid.jsonl", "w") as f:
        for item in valid:
            f.write(json.dumps(item) + "\n")

    print(f"Train: {len(train)} | Valid: {len(valid)}")
    print(f"Saved to {out_dir}/")

    # Also save alpaca format for compatibility
    alpaca_train = []
    for item in train:
        if "messages" in item:
            user = ""
            assistant = ""
            for m in item["messages"]:
                if m["role"] == "user":
                    user = m["content"]
                elif m["role"] == "assistant":
                    assistant = m["content"]
            alpaca_train.append(format_alpaca(user, assistant, "general"))

    with open(out_dir / "train_alpaca.json", "w") as f:
        json.dump(alpaca_train, f, indent=2)

    print(f"Alpaca format: {len(alpaca_train)} examples")
    print("\n✅ Dataset ready for fine-tuning")
    print("\nRecommended models for 12GB VRAM:")
    print("  • unsloth/Qwen2.5-7B-Instruct (best for instruction)")
    print("  • unsloth/gemma-2-9b-it (good all-rounder)")
    print("\nRun training with:")
    print("  cd ~/clawd/sovereign-temple && python3 train_lora.py")


if __name__ == "__main__":
    main()
