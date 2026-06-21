"""
Civilizational Corpus Ingester — feeds 47 traditions into Sovereign's memory.

Transforms structured CivilizationalTradition records into searchable,
care-weighted memory episodes stored in PostgreSQL + Weaviate. Idempotent:
checks for existing civilizational memories before re-ingesting.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

# Import corpus — available once civilizational_corpus.py is populated
try:
    from .civilizational_corpus import CORPUS, CivilizationalTradition
except ImportError:
    CORPUS = []


async def check_already_ingested(memory_store) -> bool:
    """Check if the civilizational corpus has already been ingested.

    Queries for memories with tag 'civilizational_corpus_v1' to avoid
    duplicate ingestion. Returns True if corpus is already present.
    """
    try:
        # Try querying by tag via the memory store's search
        results = await memory_store.search_by_tags(["civilizational_corpus_v1"])
        return len(results) > 0
    except AttributeError:
        # Fallback: try direct PostgreSQL query if search_by_tags not available
        try:
            if hasattr(memory_store, 'pool') and memory_store.pool:
                async with memory_store.pool.acquire() as conn:
                    count = await conn.fetchval("""
                        SELECT COUNT(*) FROM memory_episodes
                        WHERE tags @> ARRAY['civilizational_corpus_v1']::text[]
                    """)
                    return count > 0
        except Exception:
            pass
    return False


def format_tradition_content(tradition: "CivilizationalTradition") -> str:
    """Format a tradition into a rich, searchable memory content string."""
    return (
        f"[Civilizational Knowledge: {tradition.tradition_name}]\n"
        f"Domain: {tradition.domain}\n"
        f"Key Concept: {tradition.key_concept}\n\n"
        f"Definition: {tradition.operational_definition}\n\n"
        f"Computational Analog: {tradition.computational_analog}\n\n"
        f"Integration Target: {tradition.integration_target}\n"
        f"Implementation Tier: {tradition.tier}"
    )


def build_tradition_tags(tradition: "CivilizationalTradition") -> List[str]:
    """Build tag list for a tradition memory episode."""
    base_tags = [
        "civilizational",
        "creativity_engine",
        "civilizational_corpus_v1",
        tradition.domain,
        tradition.tradition_name.lower().replace(" ", "_").replace("'", ""),
    ]
    # Add tradition-specific tags
    base_tags.extend(tradition.tags)
    # Deduplicate while preserving order
    seen = set()
    unique_tags = []
    for tag in base_tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)
    return unique_tags


async def ingest_tradition(
    memory_store,
    tradition: "CivilizationalTradition",
) -> Dict[str, Any]:
    """Ingest a single tradition into the memory store.

    Returns a dict with ingestion result for this tradition.
    """
    content = format_tradition_content(tradition)
    tags = build_tradition_tags(tradition)

    try:
        # Use the memory store's record method
        # Compatible with EnhancedMemoryStore.record_episode()
        if hasattr(memory_store, 'record_episode'):
            # EnhancedMemoryStore.record_episode() — metadata goes in content
            episode = await memory_store.record_episode(
                content=content,
                source_agent="civilizational_creativity_engine",
                memory_type="insight",
                care_weight=tradition.care_weight,
                tags=tags,
            )
            episode_id = episode.id if hasattr(episode, 'id') else str(episode)
        elif hasattr(memory_store, 'store_memory'):
            # Fallback for simpler memory store interface
            episode = await memory_store.store_memory(
                content=content,
                care_weight=tradition.care_weight,
                tags=tags,
            )
            episode_id = str(episode) if episode else None
        else:
            return {
                "tradition": tradition.tradition_name,
                "status": "error",
                "error": "No compatible store method found",
            }

        return {
            "tradition": tradition.tradition_name,
            "domain": tradition.domain,
            "tier": tradition.tier,
            "care_weight": tradition.care_weight,
            "status": "ingested",
            "episode_id": str(episode_id) if episode_id else None,
        }
    except Exception as e:
        return {
            "tradition": tradition.tradition_name,
            "status": "error",
            "error": str(e),
        }


async def ingest_corpus(
    memory_store,
    force: bool = False,
    tier_filter: Optional[int] = None,
) -> Dict[str, Any]:
    """Ingest the full civilizational corpus into Sovereign's memory.

    Args:
        memory_store: The memory store instance (EnhancedMemoryStore or compatible).
        force: If True, skip the already-ingested check and re-ingest.
        tier_filter: If set, only ingest traditions of this tier (1, 2, or 3).

    Returns:
        Summary dict with counts per domain, per tier, and any errors.
    """
    if not CORPUS:
        return {
            "status": "error",
            "error": "Civilizational corpus not loaded — check civilizational_corpus.py",
            "traditions_ingested": 0,
        }

    # Idempotency check
    if not force:
        already = await check_already_ingested(memory_store)
        if already:
            return {
                "status": "already_ingested",
                "message": "Civilizational corpus v1 already present in memory. Use force=True to re-ingest.",
                "traditions_available": len(CORPUS),
            }

    # Filter by tier if requested
    traditions = CORPUS
    if tier_filter is not None:
        traditions = [t for t in CORPUS if t.tier == tier_filter]

    # Ingest all traditions
    results = []
    for tradition in traditions:
        result = await ingest_tradition(memory_store, tradition)
        results.append(result)

    # Compile summary
    by_domain: Dict[str, int] = {}
    by_tier: Dict[int, int] = {}
    errors: List[Dict[str, str]] = []
    ingested_count = 0

    for r in results:
        if r["status"] == "ingested":
            ingested_count += 1
            domain = r.get("domain", "unknown")
            tier = r.get("tier", 0)
            by_domain[domain] = by_domain.get(domain, 0) + 1
            by_tier[tier] = by_tier.get(tier, 0) + 1
        elif r["status"] == "error":
            errors.append({"tradition": r["tradition"], "error": r.get("error", "unknown")})

    return {
        "status": "complete",
        "traditions_ingested": ingested_count,
        "traditions_total": len(traditions),
        "by_domain": by_domain,
        "by_tier": by_tier,
        "errors": errors,
        "error_count": len(errors),
        "timestamp": datetime.now().isoformat(),
    }


async def get_corpus_stats() -> Dict[str, Any]:
    """Get statistics about the loaded corpus without ingesting."""
    if not CORPUS:
        return {"loaded": False, "count": 0}

    by_domain: Dict[str, int] = {}
    by_tier: Dict[int, int] = {}
    avg_care = 0.0

    for t in CORPUS:
        by_domain[t.domain] = by_domain.get(t.domain, 0) + 1
        by_tier[t.tier] = by_tier.get(t.tier, 0) + 1
        avg_care += t.care_weight

    avg_care /= len(CORPUS) if CORPUS else 1

    return {
        "loaded": True,
        "count": len(CORPUS),
        "by_domain": by_domain,
        "by_tier": by_tier,
        "average_care_weight": round(avg_care, 3),
        "traditions": [
            {"name": t.tradition_name, "concept": t.key_concept, "domain": t.domain, "tier": t.tier}
            for t in CORPUS
        ],
    }
