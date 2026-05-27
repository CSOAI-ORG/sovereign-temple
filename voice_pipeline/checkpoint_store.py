"""
Checkpoint Store — SQLite persistence for turn state.
Inspired by Nanobot's runtime checkpoint pattern.
Allows session resumption after crash or /stop.
"""
import sqlite3
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime

DB_PATH = os.environ.get("JARVIS_CHECKPOINT_DB", "/tmp/jarvis_checkpoints.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_number INTEGER NOT NULL,
            state TEXT NOT NULL,
            context TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_session ON checkpoints(session_id, turn_number DESC)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            active_model TEXT,
            metadata TEXT,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_checkpoint(session_id: str, turn_number: int, state: str, context: Dict[str, Any]):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO checkpoints (session_id, turn_number, state, context, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, turn_number, state, json.dumps(context), datetime.utcnow().isoformat()),
    )
    conn.execute(
        "INSERT OR REPLACE INTO sessions (session_id, active_model, metadata, updated_at) VALUES (?, ?, ?, ?)",
        (session_id, context.get("selected_model"), json.dumps(context), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def load_latest_checkpoint(session_id: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM checkpoints WHERE session_id = ? ORDER BY turn_number DESC LIMIT 1",
        (session_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "session_id": row["session_id"],
        "turn_number": row["turn_number"],
        "state": row["state"],
        "context": json.loads(row["context"]),
        "created_at": row["created_at"],
    }


def list_sessions() -> list:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT session_id, active_model, updated_at FROM sessions ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_session(session_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM checkpoints WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


# Auto-init on import
init_db()
