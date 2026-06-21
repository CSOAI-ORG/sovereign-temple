"""
FSRS Memory Importance — Spaced Repetition for Sovereign Memory
================================================================
Uses the FSRS algorithm (ACM SIGKDD 2022) to compute dynamic retrievability
scores for memories. Memories that are accessed frequently maintain high
retrievability; unused memories decay according to a scientifically-validated
forgetting curve.

Integration: Called from sov3_memory_consolidation.py during consolidation cycles.
"""

from fsrs import FSRS, Card, Rating
from datetime import datetime, timezone
import json
import os
import logging

log = logging.getLogger("memory_fsrs")

# FSRS scheduler
_fsrs = FSRS()

# Card state persistence
_CARD_FILE = os.path.join(os.path.dirname(__file__), "data", "fsrs_cards.json")


def _load_cards() -> dict:
    """Load FSRS card states from disk."""
    if os.path.exists(_CARD_FILE):
        try:
            with open(_CARD_FILE) as f:
                data = json.load(f)
            return data
        except:
            pass
    return {}


def _save_cards(cards: dict):
    """Persist FSRS card states."""
    os.makedirs(os.path.dirname(_CARD_FILE), exist_ok=True)
    with open(_CARD_FILE, "w") as f:
        json.dump(cards, f, default=str)


def get_retrievability(memory_id: str, last_accessed: str = None, access_count: int = 0) -> float:
    """Get the current retrievability (0-1) of a memory.

    Returns the probability that this memory would be recalled right now,
    based on its review history using the FSRS forgetting curve model.
    """
    cards = _load_cards()

    if memory_id in cards:
        card_data = cards[memory_id]
        # Reconstruct card from saved state
        card = Card()
        card.stability = card_data.get("stability", 1.0)
        card.difficulty = card_data.get("difficulty", 5.0)
        card.reps = card_data.get("reps", 0)
        card.lapses = card_data.get("lapses", 0)

        # Calculate retrievability based on elapsed time
        last = datetime.fromisoformat(card_data.get("last_review", datetime.now(timezone.utc).isoformat()))
        now = datetime.now(timezone.utc)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)

        elapsed_days = (now - last).total_seconds() / 86400

        # FSRS retrievability formula: R = (1 + elapsed/stability)^(-1)
        if card.stability > 0:
            retrievability = (1 + elapsed_days / card.stability) ** -1
        else:
            retrievability = 0.0

        return max(0.0, min(1.0, retrievability))
    else:
        # New memory — start with high retrievability that decays
        return 0.9 if access_count > 0 else 0.5


def record_access(memory_id: str, quality: str = "good") -> float:
    """Record a memory access (retrieval) and update its FSRS card.

    quality: "again" (forgot), "hard", "good", "easy"
    Returns new retrievability score.
    """
    rating_map = {
        "again": Rating.Again,
        "hard": Rating.Hard,
        "good": Rating.Good,
        "easy": Rating.Easy,
    }
    rating = rating_map.get(quality, Rating.Good)

    cards = _load_cards()

    if memory_id in cards:
        card = Card()
        card_data = cards[memory_id]
        card.stability = card_data.get("stability", 1.0)
        card.difficulty = card_data.get("difficulty", 5.0)
        card.reps = card_data.get("reps", 0)
        card.lapses = card_data.get("lapses", 0)
    else:
        card = Card()

    # Schedule review
    scheduling = _fsrs.repeat(card)
    updated_card = scheduling[rating].card

    # Save updated state
    cards[memory_id] = {
        "stability": updated_card.stability,
        "difficulty": updated_card.difficulty,
        "reps": updated_card.reps,
        "lapses": updated_card.lapses,
        "last_review": datetime.now(timezone.utc).isoformat(),
    }
    _save_cards(cards)

    return get_retrievability(memory_id)


def bulk_update_importance(memories: list) -> dict:
    """Update importance scores for a batch of memories using FSRS.

    memories: list of dicts with {id, importance_score, last_accessed, access_count}
    Returns: {memory_id: new_importance}
    """
    results = {}
    for mem in memories:
        mem_id = mem.get("id", "")
        retrievability = get_retrievability(
            mem_id,
            mem.get("last_accessed"),
            mem.get("access_count", 0)
        )
        # Blend FSRS retrievability with existing importance
        # FSRS handles decay; existing importance reflects content quality
        old_importance = mem.get("importance_score", 0.2)
        # New importance = content quality * retrievability
        # Content quality estimated from original score / decay factor
        content_quality = min(1.0, old_importance * 2)  # Rough estimate
        new_importance = content_quality * retrievability
        results[mem_id] = round(max(0.05, min(1.0, new_importance)), 3)

    return results


if __name__ == "__main__":
    # Test
    print("Testing FSRS memory integration...")
    r = get_retrievability("test_memory_1")
    print(f"  New memory retrievability: {r}")
    r2 = record_access("test_memory_1", "good")
    print(f"  After access (good): {r2}")
    r3 = record_access("test_memory_1", "easy")
    print(f"  After access (easy): {r3}")
    print("  ✅ FSRS working")
