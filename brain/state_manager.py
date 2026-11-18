"""Persistent SQLite state manager for agent sessions, execution history, and interrupt/resume workflows."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from experience.intake.hinglish import NaturalLanguageIntake
from shared.config import DATA_DIR
from shared.schemas import AgentState, TraceStep


DEFAULT_DB_PATH = DATA_DIR / "agent_sessions.db"


class StateManager:
    """Manages persistent SQLite storage of AgentState, allowing pausing on questions and seamless resumption."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.intake = NaturalLanguageIntake()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_query TEXT,
                    is_complete INTEGER DEFAULT 0,
                    is_paused INTEGER DEFAULT 0,
                    pause_reason TEXT DEFAULT '',
                    step_count INTEGER DEFAULT 0,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_session(
        self,
        session_id: str,
        state: AgentState,
        is_paused: Optional[bool] = None,
        pause_reason: Optional[str] = None,
    ) -> None:
        """Saves or updates full serialized AgentState into SQLite."""
        if is_paused is not None:
            state.is_paused = is_paused
        if pause_reason is not None:
            state.pause_reason = pause_reason

        now_str = datetime.now(timezone.utc).isoformat()
        state_dict = state.model_dump()
        state_json = json.dumps(state_dict)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT created_at FROM agent_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            created_at = row["created_at"] if row else now_str

            cursor.execute(
                """
                INSERT INTO agent_sessions (
                    session_id, user_query, is_complete, is_paused, pause_reason,
                    step_count, state_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    user_query = excluded.user_query,
                    is_complete = excluded.is_complete,
                    is_paused = excluded.is_paused,
                    pause_reason = excluded.pause_reason,
                    step_count = excluded.step_count,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    state.user_query,
                    1 if state.is_complete else 0,
                    1 if state.is_paused else 0,
                    state.pause_reason,
                    state.step_count,
                    state_json,
                    created_at,
                    now_str,
                ),
            )
            conn.commit()

    def load_session(self, session_id: str) -> Optional[AgentState]:
        """Loads and reconstructs AgentState from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT state_json FROM agent_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            data = json.loads(row["state_json"])
            return AgentState.model_validate(data)

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        """Returns metadata list of stored sessions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT session_id, user_query, is_complete, is_paused, pause_reason,
                       step_count, created_at, updated_at
                FROM agent_sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete_session(self, session_id: str) -> bool:
        """Deletes session record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM agent_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0

    def pause_session(self, session_id: str, state: AgentState, reason: str) -> AgentState:
        """Marks state as paused (e.g. waiting for citizen input) and persists to SQLite."""
        state.is_paused = True
        state.pause_reason = reason
        trace = TraceStep(
            agent_name="StateManager",
            action="Paused execution for citizen input",
            details={"session_id": session_id, "reason": reason},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        state.trace_steps.append(trace)
        self.save_session(session_id, state)
        return state

    def resume_session(self, session_id: str, citizen_reply: str) -> AgentState:
        """Resumes a paused session by parsing citizen reply, updating profile, and unpausing."""
        state = self.load_session(session_id)
        if not state:
            raise ValueError(f"Session '{session_id}' not found in state store.")

        # Parse citizen's answer into structured profile facts
        updated_profile = self.intake.parse_user_input(
            raw_text=citizen_reply,
            existing_profile=state.profile,
        )
        state.profile = updated_profile

        # Clear answered pending questions
        if state.pending_questions:
            answered_q = state.pending_questions.pop(0)
        else:
            answered_q = "Clarification"

        # Record resume trace
        trace = TraceStep(
            agent_name="StateManager",
            action=f"Resumed session with user input: '{citizen_reply[:50]}'",
            details={
                "session_id": session_id,
                "answered_question": answered_q,
                "new_known_fields": state.profile.known_fields(),
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        state.trace_steps.append(trace)

        # Unpause state and route back to planner for re-evaluating schemes
        state.is_paused = False
        state.pause_reason = ""
        state.next_node = "planner"

        # Persist updated resumed state
        self.save_session(session_id, state)
        return state
