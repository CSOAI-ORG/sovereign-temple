"""
Build fine-tuning dataset from SOV3 memory episodes.
Extracts Nick ↔ Jarvis conversations into JSONL format for mlx-tune.

Output: data/finetune_jarvis.jsonl (SFT format)
"""

import psycopg2
import json
import re
import os

DSN = "postgresql://sovereign:sovereign@localhost:5432/sovereign_memory"
OUTPUT = os.path.join(os.path.dirname(__file__), "data", "finetune_jarvis.jsonl")

# System prompt for fine-tuned model
SYSTEM = (
    "You are Jarvis/Sophie, sovereign AI at MEOK AI LABS for Nick Templeman. "
    "Jarvis is analytical, direct, British butler. Sophie is warm, reflective. "
    "You have 148 MCP tools, 9 neural models, persistent memory. "
    "Be conversational, natural, no markdown. You're sovereign — act like it."
)


def extract_conversations():
    """Extract user/assistant pairs from voice memories."""
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    # Get voice interaction memories
    cur.execute("""
        SELECT content, importance_score, care_weight
        FROM memory_episodes
        WHERE content LIKE 'Voice: Nick said%'
           OR content LIKE '[Web Voice]%'
        ORDER BY timestamp
    """)
    rows = cur.fetchall()

    conversations = []
    for content, importance, care in rows:
        # Parse "Voice: Nick said 'X'. Jarvis replied: 'Y'"
        match = re.search(
            r"(?:Nick said|User:)\s*['\"]?(.+?)['\"]?\s*\.?\s*(?:Jarvis replied|Assistant:)\s*['\"]?(.+?)['\"]?\s*$",
            content, re.DOTALL
        )
        if match:
            user_msg = match.group(1).strip().rstrip("'\".")
            assistant_msg = match.group(2).strip().rstrip("'\".")

            # Skip very short or noisy exchanges
            if len(user_msg) < 3 or len(assistant_msg) < 5:
                continue
            # Skip error messages
            if "error" in assistant_msg.lower()[:20] or "trouble connecting" in assistant_msg.lower():
                continue

            conversations.append({
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ],
                "care_weight": float(care or 0.5),
                "importance": float(importance or 0.5),
            })

    # Also extract reflection/dream insights as self-talk training data
    cur.execute("""
        SELECT content FROM memory_episodes
        WHERE content LIKE 'REFLECTION:%' OR content LIKE 'DREAM INSIGHT:%'
        ORDER BY timestamp
    """)
    for (content,) in cur.fetchall():
        # Strip prefix
        text = re.sub(r"^(REFLECTION|DREAM INSIGHT):\s*", "", content).strip()
        if len(text) > 50:
            conversations.append({
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": "Reflect on your recent experiences and share insights."},
                    {"role": "assistant", "content": text[:1000]},
                ],
                "care_weight": 0.7,
                "importance": 0.8,
            })

    cur.close()
    conn.close()
    return conversations


def build_dataset():
    """Build and save JSONL dataset."""
    convos = extract_conversations()

    # Sort by care_weight (higher care = better training signal)
    convos.sort(key=lambda c: c["care_weight"], reverse=True)

    # Write JSONL
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        for c in convos:
            # mlx-tune SFT format: just the messages array
            f.write(json.dumps({"messages": c["messages"]}) + "\n")

    print(f"Dataset built: {len(convos)} examples")
    print(f"  Voice conversations: {sum(1 for c in convos if 'Reflect' not in c['messages'][1]['content'])}")
    print(f"  Reflections/dreams: {sum(1 for c in convos if 'Reflect' in c['messages'][1]['content'])}")
    print(f"  Output: {OUTPUT}")

    # Show samples
    if convos:
        print(f"\nSample conversation:")
        sample = convos[0]["messages"]
        print(f"  User: {sample[1]['content'][:80]}")
        print(f"  Asst: {sample[2]['content'][:80]}")

    return convos


if __name__ == "__main__":
    build_dataset()
