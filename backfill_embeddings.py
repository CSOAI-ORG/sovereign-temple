#!/usr/bin/env python3
"""Backfill embeddings for SOV3 memory episodes using Ollama nomic-embed-text.

Usage:
    python3 backfill_embeddings.py          # Backfill all missing
    python3 backfill_embeddings.py --recent  # Backfill last 100 only (high-priority first)
    python3 backfill_embeddings.py --count   # Just count missing
"""
import asyncio
import sys
import time
import requests
import asyncpg

DSN = "postgresql://sovereign:sovereign@localhost:5432/sovereign_memory"
OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "nomic-embed-text"
DIM = 384  # Match pgvector column dimension
BATCH_SIZE = 20


def get_embedding(text: str) -> list:
    """Generate embedding via Ollama, truncate to 384 dims, normalize."""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "input": text[:2000],
        }, timeout=30)
        data = resp.json().get("embeddings", [])
        if data:
            raw = data[0][:DIM]
            norm = sum(x * x for x in raw) ** 0.5
            return [x / norm for x in raw] if norm > 0 else raw
    except Exception as e:
        print(f"  Embedding error: {e}")
    return None


async def backfill(recent_only=False, count_only=False):
    pool = await asyncpg.create_pool(DSN, min_size=1, max_size=3)

    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM memory_episodes")
        missing = await conn.fetchval(
            "SELECT COUNT(*) FROM memory_episodes WHERE embedding IS NULL"
        )
        print(f"Total memories: {total}")
        print(f"With embeddings: {total - missing}")
        print(f"Missing embeddings: {missing}")

        if count_only:
            await pool.close()
            return

        # Fetch memories needing embeddings — high care_weight first
        limit_clause = "LIMIT 100" if recent_only else ""
        rows = await conn.fetch(f"""
            SELECT id, content FROM memory_episodes
            WHERE embedding IS NULL
            ORDER BY care_weight DESC NULLS LAST, timestamp DESC
            {limit_clause}
        """)

    print(f"\nBackfilling {len(rows)} memories...")
    success = 0
    failed = 0
    start = time.time()

    for i, row in enumerate(rows):
        emb = get_embedding(row["content"])
        if emb:
            vec_str = "[" + ",".join(str(x) for x in emb) + "]"
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE memory_episodes SET embedding = $1::vector WHERE id = $2",
                    vec_str, row["id"],
                )
            success += 1
        else:
            failed += 1

        if (i + 1) % BATCH_SIZE == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            eta = (len(rows) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(rows)}] {success} OK, {failed} failed "
                  f"({rate:.1f}/s, ETA {eta:.0f}s)")

    elapsed = time.time() - start
    print(f"\nDone! {success} embeddings generated, {failed} failed in {elapsed:.1f}s")

    # Verify
    async with pool.acquire() as conn:
        still_missing = await conn.fetchval(
            "SELECT COUNT(*) FROM memory_episodes WHERE embedding IS NULL"
        )
        print(f"Remaining without embeddings: {still_missing}")

    await pool.close()


if __name__ == "__main__":
    count_only = "--count" in sys.argv
    recent_only = "--recent" in sys.argv
    asyncio.run(backfill(recent_only=recent_only, count_only=count_only))
