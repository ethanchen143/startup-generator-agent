import json
import sqlite3
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.config import LOGS_DIR

DB_PATH = LOGS_DIR / "session_memory.db"

class PersistentSessionStore:
    """
    Persistent SQLite-backed session store for agent memory, state snapshots, and turn histories.
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    project_id TEXT PRIMARY KEY,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_state TEXT,
                    history TEXT,
                    consolidated_summary TEXT
                )
            """)
            conn.commit()

    def save_session(self, project_id: str, state: Dict[str, Any], history: List[Dict[str, Any]], summary: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (project_id, session_state, history, consolidated_summary)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    updated_at = CURRENT_TIMESTAMP,
                    session_state = excluded.session_state,
                    history = excluded.history,
                    consolidated_summary = COALESCE(excluded.consolidated_summary, sessions.consolidated_summary)
            """, (
                project_id,
                json.dumps(state, default=str),
                json.dumps(history, default=str),
                summary
            ))
            conn.commit()

    def load_session(self, project_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_state, history, consolidated_summary FROM sessions WHERE project_id = ?", (project_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "project_id": project_id,
                    "session_state": json.loads(row[0]),
                    "history": json.loads(row[1]),
                    "consolidated_summary": row[2]
                }
            return None

def compact_history(messages: List[Dict[str, Any]], max_turns: int = 6) -> List[Dict[str, Any]]:
    """
    History compaction mechanism: Preserves system instructions and recent conversation turns,
    summarizing/condensing older history into a single compact context block to respect token limits.
    """
    if len(messages) <= max_turns:
        return messages

    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    if len(non_system_messages) <= max_turns:
        return system_messages + non_system_messages

    older_messages = non_system_messages[:-max_turns]
    recent_messages = non_system_messages[-max_turns:]

    # Summarize older turns into a compact context summary node
    summary_snippets = []
    for m in older_messages:
        role = m.get("role", "unknown")
        content = str(m.get("content", ""))[:150]
        summary_snippets.append(f"[{role}]: {content}...")

    compact_summary_node = {
        "role": "system",
        "content": f"[COMPACTED SESSION CONTEXT SUMMARY]: Historical turns compacted ({len(older_messages)} turns):\n" + "\n".join(summary_snippets)
    }

    return system_messages + [compact_summary_node] + recent_messages

async def consolidate_memory_async(project_id: str, trace_events: List[Dict[str, Any]], store: Optional[PersistentSessionStore] = None):
    """
    Async memory consolidation operation: Distills key learnings, opportunity scores, and agent trace signals
    from an active run into long-term indexed memory for persistent cross-session retrieval.
    """
    await asyncio.sleep(0.05) # Yield event loop for non-blocking async operation
    if store is None:
        store = PersistentSessionStore()

    thoughts = [t.get("content", "") for t in trace_events if t.get("event_type") in ["THOUGHT", "STATUS_CHANGE"]]
    consolidated_summary = f"Project '{project_id}' execution summary: Captured {len(trace_events)} trace events. Key insights: " + " | ".join(thoughts[:3])

    current = store.load_session(project_id)
    state = current["session_state"] if current else {}
    history = current["history"] if current else []

    store.save_session(
        project_id=project_id,
        state=state,
        history=history,
        summary=consolidated_summary
    )
    return consolidated_summary

# Singleton global instance
session_store = PersistentSessionStore()
