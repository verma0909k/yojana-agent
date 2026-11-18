"""Application Lifecycle Tracker: Persistent SQLite tracking for citizen scheme applications."""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from shared.config import DATA_DIR

DEFAULT_TRACKER_DB = DATA_DIR / "application_tracker.db"


class ApplicationTracker:
    """Manages persistent lifecycle tracking of scheme applications (DRAFT -> READY_TO_SUBMIT -> SUBMITTED)."""

    VALID_STATUSES = {
        "DRAFT",
        "IN_PROGRESS",
        "READY_TO_SUBMIT",
        "SUBMITTED",
        "APPROVED",
        "REJECTED",
    }

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_TRACKER_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS application_tasks (
                    task_id TEXT PRIMARY KEY,
                    citizen_id TEXT NOT NULL,
                    scheme_id TEXT NOT NULL,
                    scheme_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    documents_ready TEXT NOT NULL,
                    documents_missing TEXT NOT NULL,
                    pdf_path TEXT,
                    official_portal_url TEXT,
                    submission_mode TEXT DEFAULT 'ONLINE',
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_task(
        self,
        citizen_id: str,
        scheme_id: str,
        scheme_name: str,
        documents_ready: list[str],
        documents_missing: list[str],
        status: str = "DRAFT",
        pdf_path: Optional[str] = None,
        official_portal_url: str = "",
        submission_mode: str = "ONLINE",
        notes: str = "",
    ) -> dict[str, Any]:
        """Creates and persists a new application task."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {self.VALID_STATUSES}")

        task_id = f"app_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO application_tasks (
                    task_id, citizen_id, scheme_id, scheme_name, status,
                    documents_ready, documents_missing, pdf_path,
                    official_portal_url, submission_mode, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    citizen_id,
                    scheme_id,
                    scheme_name,
                    status,
                    json.dumps(documents_ready),
                    json.dumps(documents_missing),
                    str(pdf_path) if pdf_path else "",
                    official_portal_url,
                    submission_mode,
                    notes,
                    now_str,
                    now_str,
                ),
            )
            conn.commit()

        return self.get_task(task_id)

    def get_task(self, task_id: str) -> Optional[dict[str, Any]]:
        """Retrieves an application task by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM application_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["documents_ready"] = json.loads(data["documents_ready"])
            data["documents_missing"] = json.loads(data["documents_missing"])
            return data

    def list_tasks(self, citizen_id: Optional[str] = None) -> list[dict[str, Any]]:
        """Lists application tasks, optionally filtered by citizen_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if citizen_id:
                cursor.execute(
                    "SELECT * FROM application_tasks WHERE citizen_id = ? ORDER BY updated_at DESC",
                    (citizen_id,),
                )
            else:
                cursor.execute("SELECT * FROM application_tasks ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["documents_ready"] = json.loads(d["documents_ready"])
                d["documents_missing"] = json.loads(d["documents_missing"])
                results.append(d)
            return results

    def update_task_status(
        self,
        task_id: str,
        status: str,
        notes: Optional[str] = None,
        pdf_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """Updates status, notes, or pdf path of an existing application task."""
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {self.VALID_STATUSES}")

        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Application task '{task_id}' not found.")

        now_str = datetime.now(timezone.utc).isoformat()
        new_notes = f"{task['notes']}\n{notes}".strip() if notes else task["notes"]
        new_pdf = str(pdf_path) if pdf_path is not None else task["pdf_path"]

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE application_tasks
                SET status = ?, notes = ?, pdf_path = ?, updated_at = ?
                WHERE task_id = ?
                """,
                (status, new_notes, new_pdf, now_str, task_id),
            )
            conn.commit()

        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        """Deletes an application task by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM application_tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
