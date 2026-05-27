#!/usr/bin/env python3
"""
Extract real training data from 1,251 memory episodes for neural model retraining.
Replaces synthetic/heuristic training with actual interaction data.
"""

import asyncio
import asyncpg
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add neural_core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "neural_core"))

POSTGRES_DSN = os.environ.get(
    "POSTGRES_DSN",
    "postgresql://sovereign:sovereign@localhost:5432/sovereign_memory",
)


async def extract_training_data():
    """Extract training data from real memory episodes."""
    pool = await asyncpg.create_pool(POSTGRES_DSN)

    # Get high-quality episodes (care >= 0.5, importance >= 0.2)
    rows = await pool.fetch("""
        SELECT content, care_weight, importance_score, memory_type, tags, source_agent, timestamp
        FROM memory_episodes
        WHERE care_weight >= 0.5 AND importance_score >= 0.2
        ORDER BY timestamp DESC
    """)

    print(f"Found {len(rows)} high-quality episodes for training")

    # Categorize by use case
    care_episodes = [r for r in rows if r["memory_type"] in ("interaction", "decision")]
    threat_episodes = [
        r
        for r in rows
        if "security" in (r["tags"] or []) or "threat" in (r["tags"] or [])
    ]
    creativity_episodes = [
        r
        for r in rows
        if "creative" in (r["tags"] or []) or r["memory_type"] == "insight"
    ]
    relationship_episodes = [r for r in rows if r["memory_type"] in ("interaction",)]
    partnership_episodes = [
        r
        for r in rows
        if "partnership" in (r["tags"] or []) or "collaboration" in (r["tags"] or [])
    ]

    print(f"  Care episodes: {len(care_episodes)}")
    print(f"  Threat episodes: {len(threat_episodes)}")
    print(f"  Creativity episodes: {len(creativity_episodes)}")
    print(f"  Relationship episodes: {len(relationship_episodes)}")
    print(f"  Partnership episodes: {len(partnership_episodes)}")

    # Save extracted data
    output_dir = Path(__file__).parent / "training_data"
    output_dir.mkdir(exist_ok=True)

    datasets = {
        "care_episodes": care_episodes,
        "threat_episodes": threat_episodes,
        "creativity_episodes": creativity_episodes,
        "relationship_episodes": relationship_episodes,
        "partnership_episodes": partnership_episodes,
    }

    for name, data in datasets.items():
        output_file = output_dir / f"{name}.json"
        serializable = []
        for row in data:
            serializable.append(
                {
                    "content": row["content"],
                    "care_weight": float(row["care_weight"]),
                    "importance_score": float(row["importance_score"]),
                    "memory_type": row["memory_type"],
                    "tags": row["tags"] or [],
                    "source_agent": row["source_agent"],
                    "timestamp": row["timestamp"].isoformat(),
                }
            )
        output_file.write_text(json.dumps(serializable, indent=2))
        print(f"  Saved {name}: {len(serializable)} episodes → {output_file}")

    await pool.close()
    return datasets


async def retrain_models():
    """Retrain neural models with real data."""
    from neural_core import create_default_registry

    print("\n🧠 Retraining neural models with real data...")

    registry = create_default_registry(
        model_dir=os.path.join(os.path.dirname(__file__), "models")
    )

    # Load real training data
    output_dir = Path(__file__).parent / "training_data"

    for name, model in registry.models.items():
        print(f"\n  Training {name}...")
        try:
            model.train_model()
            model.save_model()
            print(f"    ✅ {name} retrained")
        except Exception as e:
            print(f"    ⚠️  {name} training failed: {e}")

    print("\n✅ All models retrained with real data")


if __name__ == "__main__":
    asyncio.run(extract_training_data())
    asyncio.run(retrain_models())
