#!/usr/bin/env python3
"""
Master Memory Ingestion — Ingest ALL episodic memory sources into Reflection Engine.
Sources:
  1. ~/clawd/jarvis-memory/ (already partially ingested)
  2. ~/clawd/memory/*.md (14,538 lines of session logs)
  3. ~/clawd/memory/experiences.jsonl (367 experiences)
  4. ~/clawd/sovereign-temple/memory/episodic/ (461 files)
  5. ~/clawd/sovereign-temple/memory/semantic/ (15 files)
"""
import json
import os
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/Users/nicholas/clawd/sovereign-temple")
from reflection_engine import ReflectionEngine

re_engine = ReflectionEngine()
stats = {"inserted": 0, "duplicates": 0, "errors": 0, "sources": {}}


def slugify(text: str, max_len: int = 80) -> str:
    return re.sub(r"[^\w\s]", "", text).strip()[:max_len]


def reflect(task_type: str, task_input: str, task_summary: str, model_used: str = "unknown", latency_ms: float = 0, success: bool = True):
    try:
        re_engine.reflect(
            task_type=task_type,
            task_input=task_input,
            task_summary=task_summary,
            model_used=model_used,
            latency_ms=latency_ms,
            tokens_in=len(task_input.split()),
            tokens_out=len(task_summary.split()),
            care_score=0.7,
            success=success,
        )
        stats["inserted"] += 1
    except sqlite3.IntegrityError:
        stats["duplicates"] += 1
    except Exception as e:
        stats["errors"] += 1
        print(f"    ⚠️ Reflect error: {e}")


def ingest_markdown_logs():
    """Ingest ~/clawd/memory/*.md session logs."""
    mem_dir = Path("/Users/nicholas/clawd/memory")
    md_files = sorted(mem_dir.glob("*.md"))
    print(f"\n📁 Markdown logs: {len(md_files)} files")

    for f in md_files:
        text = f.read_text(errors="ignore")
        lines = text.splitlines()
        # Chunk into ~200-line segments
        chunk_size = 200
        for i in range(0, len(lines), chunk_size):
            chunk = "\n".join(lines[i:i + chunk_size]).strip()
            if len(chunk) < 50:
                continue
            title = slugify(lines[0] if lines else f.name)
            reflect(
                task_type="session_log",
                task_input=f"[{f.name}] {title}",
                task_summary=chunk[:500],
                model_used="session_archive",
                latency_ms=0,
            )
    stats["sources"]["markdown_logs"] = stats["inserted"]


def ingest_experiences_jsonl():
    """Ingest ~/clawd/memory/experiences.jsonl."""
    path = Path("/Users/nicholas/clawd/memory/experiences.jsonl")
    if not path.exists():
        return

    print(f"\n📁 experiences.jsonl")
    count = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                exp_type = data.get("type", "experience")
                outcome = data.get("outcome", "unknown")
                iteration = data.get("iteration", 0)
                ts = data.get("timestamp", 0)
                reflect(
                    task_type="experience",
                    task_input=f"{exp_type} iteration {iteration} at {ts}",
                    task_summary=json.dumps(data, default=str)[:500],
                    model_used="experience_forge",
                    latency_ms=0,
                    success=outcome == "success",
                )
                count += 1
            except json.JSONDecodeError:
                stats["errors"] += 1
    stats["sources"]["experiences_jsonl"] = count
    print(f"   Processed {count} experience entries")


def ingest_episodic_memories():
    """Ingest ~/clawd/sovereign-temple/memory/episodic/ files."""
    episodic_dir = Path("/Users/nicholas/clawd/sovereign-temple/memory/episodic")
    if not episodic_dir.exists():
        return

    files = list(episodic_dir.glob("*"))
    print(f"\n📁 Episodic memories: {len(files)} files")
    count = 0
    for f in files:
        try:
            text = f.read_text(errors="ignore").strip()
            if len(text) < 20:
                continue
            reflect(
                task_type="episodic",
                task_input=f.name,
                task_summary=text[:500],
                model_used="episodic_memory",
                latency_ms=0,
            )
            count += 1
        except Exception as e:
            stats["errors"] += 1
    stats["sources"]["episodic"] = count
    print(f"   Processed {count} episodic entries")


def ingest_semantic_memories():
    """Ingest ~/clawd/sovereign-temple/memory/semantic/ files."""
    semantic_dir = Path("/Users/nicholas/clawd/sovereign-temple/memory/semantic")
    if not semantic_dir.exists():
        return

    files = list(semantic_dir.glob("*"))
    print(f"\n📁 Semantic memories: {len(files)} files")
    count = 0
    for f in files:
        try:
            text = f.read_text(errors="ignore").strip()
            if len(text) < 20:
                continue
            reflect(
                task_type="semantic",
                task_input=f.name,
                task_summary=text[:500],
                model_used="semantic_memory",
                latency_ms=0,
            )
            count += 1
        except Exception as e:
            stats["errors"] += 1
    stats["sources"]["semantic"] = count
    print(f"   Processed {count} semantic entries")


def main():
    print("=" * 60)
    print("MASTER MEMORY INGESTION")
    print("=" * 60)

    # Check existing count
    db_path = "/Users/nicholas/clawd/sovereign-temple/data/reflection_store.db"
    conn = sqlite3.connect(db_path)
    before = conn.execute("SELECT COUNT(*) FROM reflections").fetchone()[0]
    conn.close()
    print(f"Starting with {before} existing reflections")

    ingest_markdown_logs()
    ingest_experiences_jsonl()
    ingest_episodic_memories()
    ingest_semantic_memories()

    # Final count
    conn = sqlite3.connect(db_path)
    after = conn.execute("SELECT COUNT(*) FROM reflections").fetchone()[0]
    conn.close()

    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Before: {before}")
    print(f"After:  {after}")
    print(f"New:    {after - before}")
    print(f"Errors: {stats['errors']}")
    print(f"Duplicates: {stats['duplicates']}")
    print("\nBy source:")
    for src, cnt in stats["sources"].items():
        print(f"  {src}: {cnt}")


if __name__ == "__main__":
    main()
