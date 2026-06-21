#!/usr/bin/env python3
"""
Jarvis Memory Corpus Ingestion Script
Ingests Jarvis memory files into the MEOKCLAW Dual-Brain Reflection Engine.
"""
import json
import os
import sys
import hashlib
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, Any, List, Optional

# Ensure CWD is sovereign-temple for correct relative DB paths
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(_SCRIPT_DIR)

from reflection_engine import ReflectionEngine
from skill_library import SkillLibrary


MEMORY_DIR = os.path.expanduser("~/clawd/jarvis-memory")

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def load_json(path: str) -> List[Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def emotion_to_care_score(emotion: str) -> float:
    mapping = {
        "excited": 0.95,
        "happy": 0.9,
        "calm": 0.85,
        "neutral": 0.8,
        "tired": 0.6,
        "stressed": 0.5,
        "frustrated": 0.4,
        "angry": 0.3,
        "sad": 0.4,
    }
    return mapping.get(emotion.lower(), 0.8)


def truncate(text: str, length: int = 500) -> str:
    return text[:length] if text else ""


# ----------------------------------------------------------------------
# Ingestors
# ----------------------------------------------------------------------

def ingest_conversations(engine: ReflectionEngine) -> Dict[str, Any]:
    """Process assistant messages as response_generation tasks."""
    data = load_json(os.path.join(MEMORY_DIR, "conversations.json"))
    stats = {"processed": 0, "skills": 0, "errors": []}

    for session_idx, session_obj in enumerate(data):
        try:
            session = session_obj.get("session", {})
            messages = session.get("messages", [])

            for i, msg in enumerate(messages):
                if msg.get("role") != "assistant":
                    continue

                # Find preceding user message
                user_content = ""
                for j in range(i - 1, -1, -1):
                    if messages[j].get("role") == "user":
                        user_content = messages[j].get("content", "")
                        break

                task_input = truncate(user_content, 400)
                task_summary = truncate(msg.get("content", ""), 500)
                emotion = msg.get("emotion", "neutral")

                try:
                    skill_hash = engine.reflect(
                        task_type="response_generation",
                        task_input=task_input,
                        task_summary=task_summary,
                        model_used="jarvis",
                        latency_ms=0.0,
                        tokens_in=len(task_input),
                        tokens_out=len(task_summary),
                        care_score=emotion_to_care_score(emotion),
                        success=True,
                    )
                    stats["processed"] += 1
                    if skill_hash:
                        stats["skills"] += 1
                except Exception as e:
                    stats["errors"].append(f"session {session_idx} msg {i}: {e}")
        except Exception as e:
            stats["errors"].append(f"session {session_idx}: {e}")

    return stats


def ingest_emotion_log(engine: ReflectionEngine) -> Dict[str, Any]:
    data = load_json(os.path.join(MEMORY_DIR, "emotion_log.json"))
    stats = {"processed": 0, "skills": 0, "errors": []}

    for entry in data:
        try:
            emotion = entry.get("emotion", "neutral")
            intensity = entry.get("intensity", 0.5)
            context = entry.get("context", "")

            skill_hash = engine.reflect(
                task_type="emotion_observation",
                task_input=truncate(context, 400),
                task_summary=f"Detected {emotion} emotion with intensity {intensity}",
                model_used="jarvis",
                latency_ms=0.0,
                tokens_in=len(context),
                tokens_out=50,
                care_score=float(intensity),
                success=True,
            )
            stats["processed"] += 1
            if skill_hash:
                stats["skills"] += 1
        except Exception as e:
            stats["errors"].append(str(e))

    return stats


def ingest_execution_log(engine: ReflectionEngine) -> Dict[str, Any]:
    data = load_json(os.path.join(MEMORY_DIR, "execution-log.json"))
    stats = {"processed": 0, "skills": 0, "errors": []}

    for entry in data:
        try:
            action = entry.get("action", "unknown")
            command = str(entry.get("command", ""))
            output = str(entry.get("output", "")) if entry.get("output") is not None else ""
            error = entry.get("error")

            success = error is None
            task_summary = truncate(output, 400) if success else f"Error: {truncate(str(error), 300)}"

            skill_hash = engine.reflect(
                task_type=action,
                task_input=truncate(command, 400),
                task_summary=task_summary,
                model_used="jarvis",
                latency_ms=0.0,
                tokens_in=len(command),
                tokens_out=len(output),
                care_score=0.8 if success else 0.3,
                success=success,
                error_message=truncate(str(error), 400) if error else None,
            )
            stats["processed"] += 1
            if skill_hash:
                stats["skills"] += 1
        except Exception as e:
            stats["errors"].append(str(e))

    return stats


def ingest_session_summaries(engine: ReflectionEngine) -> Dict[str, Any]:
    data = load_json(os.path.join(MEMORY_DIR, "session_summaries.json"))
    stats = {"processed": 0, "skills": 0, "errors": []}

    for entry in data:
        try:
            first_msg = entry.get("first_user_msg", "")
            topics = entry.get("topics", "")
            msg_count = entry.get("message_count", 0)
            emotions = entry.get("emotions", [])

            task_summary = f"Session: {msg_count} messages. Topics: {truncate(topics, 300)}"

            care_score = 0.85
            if any(e in {"stressed", "frustrated", "angry"} for e in emotions):
                care_score = 0.55
            elif any(e in {"tired"} for e in emotions):
                care_score = 0.65
            elif any(e in {"excited", "happy"} for e in emotions):
                care_score = 0.92

            skill_hash = engine.reflect(
                task_type="session_summary",
                task_input=truncate(first_msg, 400),
                task_summary=task_summary,
                model_used="jarvis",
                latency_ms=0.0,
                tokens_in=entry.get("user_messages", 0) * 50,
                tokens_out=entry.get("jarvis_messages", 0) * 100,
                care_score=care_score,
                success=True,
            )
            stats["processed"] += 1
            if skill_hash:
                stats["skills"] += 1
        except Exception as e:
            stats["errors"].append(str(e))

    return stats


# ----------------------------------------------------------------------
# Skill Pattern Builder
# ----------------------------------------------------------------------

def sync_individual_skills(engine: ReflectionEngine, skill_lib: SkillLibrary) -> Dict[str, Any]:
    """Copy auto-extracted skills from reflections into the skill library."""
    import sqlite3
    stats = {"inserted": 0, "duplicates": 0, "errors": 0}

    conn = sqlite3.connect(engine.db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT DISTINCT skill_hash, task_type, task_summary, skill_extracted, care_score
        FROM reflections
        WHERE skill_hash IS NOT NULL
    """).fetchall()
    conn.close()

    for row in rows:
        try:
            yaml_body = row["skill_extracted"] or ""
            title = row["task_type"].replace("_", " ").title()
            desc = truncate(row["task_summary"], 200)

            is_new = skill_lib.ingest(
                skill_hash=row["skill_hash"],
                task_type=row["task_type"],
                title=title,
                description=desc,
                yaml_body=yaml_body,
                care_score=row["care_score"] or 0.8,
            )
            if is_new:
                stats["inserted"] += 1
            else:
                stats["duplicates"] += 1
        except Exception as e:
            stats["errors"] += 1

    return stats


def build_recurring_skills(engine: ReflectionEngine, skill_lib: SkillLibrary) -> Dict[str, Any]:
    """Build consolidated skills from recurring task_type patterns."""
    import sqlite3
    stats = {"inserted": 0, "duplicates": 0, "errors": 0}

    conn = sqlite3.connect(engine.db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT task_type,
               COUNT(*) as cnt,
               AVG(care_score) as avg_care,
               GROUP_CONCAT(DISTINCT task_summary) as summaries
        FROM reflections
        GROUP BY task_type
        HAVING cnt >= 3
        ORDER BY cnt DESC
    """).fetchall()
    conn.close()

    for row in rows:
        task_type = row["task_type"]
        count = row["cnt"]
        avg_care = row["avg_care"] or 0.8
        summaries = str(row["summaries"] or "")[:400]

        yaml_body = f"""# Skill: {task_type.replace('_', ' ').title()}
# Extracted: {datetime.utcnow().isoformat()}
# Source: Jarvis Memory Ingestion (recurring pattern)
# Frequency: {count} occurrences

task_type: {task_type}
description: >
  {summaries}
validation:
  care_score_min: {round(float(avg_care) * 0.8, 2)}
  max_latency_ms: 5000
"""
        skill_hash = hashlib.sha256(yaml_body.encode()).hexdigest()[:16]

        try:
            is_new = skill_lib.ingest(
                skill_hash=skill_hash,
                task_type=task_type,
                title=f"{task_type.replace('_', ' ').title()} Pattern",
                description=f"Recurring pattern from {count} Jarvis memory entries. {truncate(summaries, 200)}",
                yaml_body=yaml_body,
                care_score=round(float(avg_care), 2),
            )
            if is_new:
                stats["inserted"] += 1
            else:
                stats["duplicates"] += 1
        except Exception as e:
            stats["errors"] += 1
            print(f"  [ERROR] Skill ingest for {task_type}: {e}")

    return stats


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main():
    print("=" * 70)
    print("JARVIS MEMORY CORPUS — MEOKCLAW DUAL-BRAIN INGESTION")
    print("=" * 70)

    engine = ReflectionEngine()
    skill_lib = SkillLibrary()

    print(f"\nReflection store : {engine.db_path}")
    print(f"Skill library    : {skill_lib.db_path}")
    print(f"Memory source    : {MEMORY_DIR}")

    pre_stats = engine.stats()
    pre_skill_stats = skill_lib.stats()
    print(f"\nPre-ingestion  — Reflections: {pre_stats['total_reflections']}, Skills: {pre_skill_stats['total_skills']}")

    # Ingest all corpora
    results = {}

    print("\n[1/4] Ingesting conversation messages (response_generation)...")
    results["conversations"] = ingest_conversations(engine)
    print(f"      Processed: {results['conversations']['processed']}, Skills extracted: {results['conversations']['skills']}, Errors: {len(results['conversations']['errors'])}")

    print("\n[2/4] Ingesting emotion log (emotion_observation)...")
    results["emotion_log"] = ingest_emotion_log(engine)
    print(f"      Processed: {results['emotion_log']['processed']}, Skills extracted: {results['emotion_log']['skills']}, Errors: {len(results['emotion_log']['errors'])}")

    print("\n[3/4] Ingesting execution log (action tasks)...")
    results["execution_log"] = ingest_execution_log(engine)
    print(f"      Processed: {results['execution_log']['processed']}, Skills extracted: {results['execution_log']['skills']}, Errors: {len(results['execution_log']['errors'])}")

    print("\n[4/4] Ingesting session summaries...")
    results["session_summaries"] = ingest_session_summaries(engine)
    print(f"      Processed: {results['session_summaries']['processed']}, Skills extracted: {results['session_summaries']['skills']}, Errors: {len(results['session_summaries']['errors'])}")

    # Build skills
    print("\n[SKILL SYNC] Syncing auto-extracted skills to Skill Library...")
    sync_stats = sync_individual_skills(engine, skill_lib)
    print(f"      Inserted: {sync_stats['inserted']}, Duplicates: {sync_stats['duplicates']}, Errors: {sync_stats['errors']}")

    print("\n[SKILL BUILD] Building skill embeddings from recurring patterns...")
    pattern_stats = build_recurring_skills(engine, skill_lib)
    print(f"      Inserted: {pattern_stats['inserted']}, Duplicates: {pattern_stats['duplicates']}, Errors: {pattern_stats['errors']}")

    # Final stats
    post_stats = engine.stats()
    post_skill_stats = skill_lib.stats()
    total_reflections = post_stats["total_reflections"] - pre_stats["total_reflections"]

    print("\n" + "=" * 70)
    print("INGESTION REPORT")
    print("=" * 70)
    print(f"Reflections ingested : +{total_reflections}")
    print(f"  - conversations    : {results['conversations']['processed']}")
    print(f"  - emotion_log      : {results['emotion_log']['processed']}")
    print(f"  - execution_log    : {results['execution_log']['processed']}")
    print(f"  - session_summaries: {results['session_summaries']['processed']}")
    print(f"Unique skills (DB)   : {post_stats['unique_skills']}")
    print(f"Success rate         : {post_stats['success_rate']}%")
    print(f"Skill Library        : {post_skill_stats['total_skills']} total ({post_skill_stats['validated_skills']} validated)")
    print(f"Avg care score       : {post_skill_stats['avg_care_score']}")

    total_errors = sum(len(r["errors"]) for r in results.values())
    if total_errors > 0:
        print(f"\nErrors encountered   : {total_errors}")
        for source, result in results.items():
            for err in result["errors"][:3]:
                print(f"  [{source}] {err}")
            if len(result["errors"]) > 3:
                print(f"  ... and {len(result['errors']) - 3} more from {source}")
    else:
        print("\nNo errors encountered.")

    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
