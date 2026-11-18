"""Memory store (SQLite) and proactive scheme monitor (APScheduler)."""

import sqlite3
import json
from pathlib import Path
from typing import Optional
from shared.config import DATA_DIR
from shared.schemas import CitizenProfile, MatchResult

DB_PATH = DATA_DIR / "yojana_memory.db"


class MemoryStore:
    """Stores user profiles, matching history, and monitored alerts in SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS citizens (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS match_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    matches_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_profile(self, user_id: str, profile: CitizenProfile):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO citizens (user_id, profile_json) VALUES (?, ?)",
                (user_id, profile.model_dump_json())
            )
            conn.commit()

    def get_profile(self, user_id: str) -> Optional[CitizenProfile]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT profile_json FROM citizens WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return CitizenProfile.model_validate_json(row[0])
        return None

    def save_matches(self, user_id: str, matches: list[MatchResult]):
        matches_data = [m.model_dump() for m in matches]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO match_history (user_id, matches_json) VALUES (?, ?)",
                (user_id, json.dumps(matches_data))
            )
            conn.commit()
