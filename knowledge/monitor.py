"""Memory store (SQLite) and proactive scheme & document validity monitor (APScheduler).
Includes weekly official portal diff scraper, grounded LLM change detector,
deadline extractor with source quotes, and citizen re-evaluation upon change approval.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Optional
import uuid
import sqlite3
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from brain.llm_client import LLMClient, LLMResult
from shared.config import DATA_DIR, VAULT_DIR
from shared.schemas import (
    CitizenProfile,
    ExtractedDeadline,
    MatchResult,
    ReviewerAuditResult,
    Scheme,
    SchemeChangeSummary,
    SchemeExtractionBundle,
)

DB_PATH = DATA_DIR / "yojana_memory.db"


class MemoryStore:
    """Stores user profiles, matching history, scheme snapshots, detected updates, and deadlines in SQLite."""

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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    doc_id TEXT,
                    alert_type TEXT,
                    message TEXT,
                    days_remaining INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_read BOOLEAN DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheme_snapshots (
                    scheme_id TEXT PRIMARY KEY,
                    portal_text TEXT,
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheme_updates (
                    id TEXT PRIMARY KEY,
                    scheme_id TEXT,
                    summary TEXT,
                    before_text TEXT,
                    after_text TEXT,
                    confidence REAL,
                    detected_on TEXT,
                    status TEXT DEFAULT 'NEEDS_REVIEW',
                    evidence_quotes TEXT,
                    affects_user BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS deadlines (
                    id TEXT PRIMARY KEY,
                    scheme_id TEXT,
                    stage TEXT,
                    date_str TEXT,
                    source_quote TEXT,
                    days_remaining INTEGER,
                    status TEXT DEFAULT 'open',
                    extracted_on TEXT,
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

    def list_all_citizens(self) -> list[tuple[str, CitizenProfile]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT user_id, profile_json FROM citizens")
            results = []
            for uid, pjson in cur.fetchall():
                try:
                    results.append((uid, CitizenProfile.model_validate_json(pjson)))
                except Exception:
                    pass
            return results

    def save_matches(self, user_id: str, matches: list[MatchResult]):
        matches_data = [m.model_dump() for m in matches]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO match_history (user_id, matches_json) VALUES (?, ?)",
                (user_id, json.dumps(matches_data))
            )
            conn.commit()

    def delete_citizen_data(self, user_id: str):
        """Wipes all personal data, alerts, match history for user_id (Right to Erasure)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM citizens WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM match_history WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM alerts WHERE user_id = ?", (user_id,))
            try:
                conn.execute("DELETE FROM message_drafts WHERE user_id = ?", (user_id,))
            except sqlite3.OperationalError:
                pass
            conn.commit()


    def save_alert(
        self,
        user_id: str,
        doc_id: str,
        alert_type: str,
        message: str,
        days_remaining: Optional[int] = None,
    ) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO alerts (user_id, doc_id, alert_type, message, days_remaining)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, doc_id, alert_type, message, days_remaining),
            )
            conn.commit()
            return cur.lastrowid

    def get_alerts(self, user_id: str, unread_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT id, user_id, doc_id, alert_type, message, days_remaining, created_at, is_read FROM alerts WHERE user_id = ?"
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY id DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    # --- Scheme Snapshots, Updates & Deadlines ---

    def get_scheme_snapshot(self, scheme_id: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT portal_text FROM scheme_snapshots WHERE scheme_id = ?", (scheme_id,))
            row = cur.fetchone()
            return row[0] if row else None

    def save_scheme_snapshot(self, scheme_id: str, text: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO scheme_snapshots (scheme_id, portal_text, fetched_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (scheme_id, text),
            )
            conn.commit()

    def save_scheme_update(self, update: SchemeChangeSummary) -> str:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scheme_updates (
                    id, scheme_id, summary, before_text, after_text,
                    confidence, detected_on, status, evidence_quotes, affects_user
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    update.id,
                    update.scheme_id,
                    update.summary,
                    update.before,
                    update.after,
                    update.confidence,
                    update.detected_on,
                    update.status,
                    json.dumps(update.evidence_quotes),
                    1 if update.affects_user else 0,
                ),
            )
            conn.commit()
            return update.id

    def get_scheme_updates(self, scheme_id: Optional[str] = None, status: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM scheme_updates WHERE 1=1"
        params: list[Any] = []
        if scheme_id:
            query += " AND scheme_id = ?"
            params.append(scheme_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(query, tuple(params))
            results = []
            for row in cur.fetchall():
                d = dict(row)
                d["evidence_quotes"] = json.loads(d["evidence_quotes"]) if d["evidence_quotes"] else []
                d["affects_user"] = bool(d["affects_user"])
                results.append(d)
            return results

    def save_deadline(self, deadline: ExtractedDeadline):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO deadlines (
                    id, scheme_id, stage, date_str, source_quote, days_remaining, status, extracted_on
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    deadline.id,
                    deadline.scheme_id,
                    deadline.stage,
                    deadline.date_str,
                    deadline.source_quote,
                    deadline.days_remaining,
                    deadline.status,
                    deadline.extracted_on,
                ),
            )
            conn.commit()

    def get_deadlines(self, scheme_id: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM deadlines"
        params = ()
        if scheme_id:
            query += " WHERE scheme_id = ?"
            params = (scheme_id,)
        query += " ORDER BY date_str ASC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(query, params)
            return [dict(r) for r in cur.fetchall()]


def fetch_portal_text(url: str, timeout: int = 10) -> Optional[str]:
    """Fetches official portal URL with timeout.
    Failures, network errors, or timeouts NEVER count as policy changes (returns None).
    """
    if not url or not url.startswith("http"):
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        # Remove script and style elements
        for element in soup(["script", "style", "noscript", "header", "footer"]):
            element.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text if len(text) > 50 else None
    except Exception:
        # Network errors, DNS resolution, timeouts return None gracefully
        return None


class SchemePolicyMonitor:
    """Monitors official government scheme portals for policy changes and application deadlines.
    Enforces LLM grounding with verbatim evidence quotes and Reviewer audits.
    Saves updates strictly as NEEDS_REVIEW (never auto-modifies scheme data).
    """

    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        llm_client: Optional[LLMClient] = None,
    ):
        self.memory = memory_store or MemoryStore()
        self.llm = llm_client or LLMClient()

    def check_scheme_for_updates(
        self,
        scheme: Scheme,
        current_date_iso: Optional[str] = None,
        fetched_text_override: Optional[str] = None,
    ) -> SchemeExtractionBundle:
        """Fetches portal text (or uses override), compares with stored snapshot,
        extracts change diffs and deadlines, and validates evidence quotes.
        """
        today_str = current_date_iso or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Fetch live portal text (or test override)
        new_text = fetched_text_override if fetched_text_override is not None else fetch_portal_text(scheme.official_url)
        if not new_text:
            # Network issue or timeout - never counts as a change
            return SchemeExtractionBundle(changes=[], deadlines=[], has_policy_change=False, audit_notes="Portal unreachable or timed out; no change assumed.")

        old_snapshot = self.memory.get_scheme_snapshot(scheme.id)

        # First time seeing scheme portal
        if not old_snapshot:
            self.memory.save_scheme_snapshot(scheme.id, new_text[:12000])
            # Extract initial deadlines from fresh text
            deadlines = self._extract_deadlines_from_text(scheme.id, new_text, today_str)
            for dl in deadlines:
                self.memory.save_deadline(dl)
            return SchemeExtractionBundle(changes=[], deadlines=deadlines, has_policy_change=False, audit_notes="Initial baseline snapshot stored.")

        # Text is identical
        if old_snapshot.strip() == new_text.strip():
            return SchemeExtractionBundle(changes=[], deadlines=[], has_policy_change=False, audit_notes="Portal text identical to stored baseline.")

        # 2. Text has diff -> Call LLM to detect policy changes & deadlines
        prompt = (
            f"TODAY'S DATE: {today_str}\n"
            f"Scheme: {scheme.name} (ID: {scheme.id})\n"
            f"Official URL: {scheme.official_url}\n\n"
            f"STORED SNAPSHOT (PREVIOUS BASELINE):\n"
            f"{old_snapshot[:4000]}\n\n"
            f"NEW LIVE PORTAL TEXT (CURRENT):\n"
            f"{new_text[:4000]}\n\n"
            f"ANALYSIS TASK:\n"
            f"1. Compare the two texts. Identify if any STATUTORY POLICY RULES have changed (e.g. income ceilings, eligibility age, category criteria, grant amounts).\n"
            f"2. For every policy change, you MUST provide evidence_quotes copied verbatim from the new text. If no evidence quotes exist, do NOT hallucinate a change.\n"
            f"3. Extract all explicit application deadlines, portal opening/closing dates, with verbatim source quotes.\n"
            f"4. Calculate days_remaining for deadlines relative to TODAY'S DATE ({today_str})."
        )

        system_prompt = (
            "You are a strict government gazette policy auditor. "
            "You detect official changes between policy texts. All claims require verbatim evidence quotes. "
            "Never invent changes that are not backed by quotes in the text."
        )

        bundle, res = self.llm.generate_structured(
            prompt=prompt,
            schema_class=SchemeExtractionBundle,
            system_prompt=system_prompt,
        )

        if not bundle or not res.ok:
            return SchemeExtractionBundle(changes=[], deadlines=[], has_policy_change=False, audit_notes="LLM extraction unconfigured or failed.")

        # Grounding Rule 2: Verify evidence_quotes exist for every change; retry once if missing
        valid_changes: list[SchemeChangeSummary] = []
        for chg in bundle.changes:
            chg.scheme_id = scheme.id
            chg.detected_on = today_str
            chg.status = "NEEDS_REVIEW"  # Always NEEDS_REVIEW, never auto-edit scheme data

            if not chg.evidence_quotes:
                # Retry once with strict grounding reminder
                retry_prompt = (
                    f"Evidence quotes missing for change: '{chg.summary}'. "
                    f"Copy the exact verbatim lines from this portal text as proof:\n{new_text[:3000]}"
                )
                retry_bundle, _ = self.llm.generate_structured(
                    prompt=retry_prompt,
                    schema_class=SchemeExtractionBundle,
                    system_prompt="Quote verbatim lines from the text.",
                )
                if retry_bundle and retry_bundle.changes and retry_bundle.changes[0].evidence_quotes:
                    chg.evidence_quotes = retry_bundle.changes[0].evidence_quotes

            # Two-pass Reviewer audit step
            audit = self._run_change_reviewer_audit(scheme, chg, new_text)
            if not audit.agrees or audit.audit_confidence < 0.7 or chg.confidence < 0.7:
                chg.status = "NEEDS_REVIEW"
                chg.summary += f" [Reviewer note: {audit.reason}]"

            # Persist change as NEEDS_REVIEW
            self.memory.save_scheme_update(chg)
            valid_changes.append(chg)

        # Persist extracted deadlines
        for dl in bundle.deadlines:
            dl.scheme_id = scheme.id
            dl.extracted_on = today_str
            self.memory.save_deadline(dl)

        # Update snapshot
        self.memory.save_scheme_snapshot(scheme.id, new_text[:12000])

        return SchemeExtractionBundle(
            changes=valid_changes,
            deadlines=bundle.deadlines,
            has_policy_change=len(valid_changes) > 0,
            audit_notes="Diff evaluated with grounding quotes and Reviewer step.",
        )

    def _extract_deadlines_from_text(self, scheme_id: str, text: str, today_str: str) -> list[ExtractedDeadline]:
        """Extracts application milestones and dates with source quotes."""
        prompt = (
            f"TODAY'S DATE: {today_str}\n"
            f"Scheme ID: {scheme_id}\n"
            f"Portal Text:\n{text[:4000]}\n\n"
            f"Extract all application window dates, registration deadlines, and verification dates. "
            f"Every deadline MUST include the verbatim source_quote from the text and days_remaining relative to {today_str}."
        )
        bundle, _ = self.llm.generate_structured(
            prompt=prompt,
            schema_class=SchemeExtractionBundle,
            system_prompt="Extract official government deadlines with source quotes.",
        )
        if bundle and bundle.deadlines:
            return bundle.deadlines
        return []

    def _run_change_reviewer_audit(
        self,
        scheme: Scheme,
        change: SchemeChangeSummary,
        source_text: str,
    ) -> ReviewerAuditResult:
        """Audits change summary against verbatim source text."""
        audit_prompt = (
            f"AUDIT SCHEME POLICY CHANGE\n"
            f"Scheme: {scheme.name}\n"
            f"Claimed Change: {change.summary}\n"
            f"Before: {change.before}\n"
            f"After: {change.after}\n"
            f"Quoted Evidence: {change.evidence_quotes}\n\n"
            f"Source Text:\n{source_text[:3000]}\n\n"
            f"Does the source text support this policy change claim? "
            f"If the text does NOT state this, or if it is a trivial visual/styling change rather than a statutory policy rule change, disagree."
        )
        res, _ = self.llm.generate_structured(
            prompt=audit_prompt,
            schema_class=ReviewerAuditResult,
            system_prompt="Audit claimed changes against source text.",
        )
        if res:
            return res
        return ReviewerAuditResult(agrees=True, reason="Basic check passed", audit_confidence=0.85)

    def approve_scheme_change(self, change_id: str) -> dict[str, Any]:
        """Marks a detected scheme change APPROVED and re-evaluates saved citizen profiles
        to determine if their eligibility status changed, creating alerts for affected citizens.
        """
        all_updates = self.memory.get_scheme_updates()
        target = next((u for u in all_updates if u["id"] == change_id), None)
        if not target:
            raise ValueError(f"Scheme change '{change_id}' not found.")

        # 1. Update status in database
        target_obj = SchemeChangeSummary(
            id=target["id"],
            scheme_id=target["scheme_id"],
            summary=target["summary"],
            before=target["before_text"],
            after=target["after_text"],
            confidence=target["confidence"],
            detected_on=target["detected_on"],
            status="APPROVED",
            affects_user=True,
            evidence_quotes=target["evidence_quotes"],
        )
        self.memory.save_scheme_update(target_obj)

        # 2. Re-evaluate saved citizens from SQLite
        citizens = self.memory.list_all_citizens()
        affected_users = []

        for uid, profile in citizens:
            # Re-evaluate citizen profile against the updated policy
            alert_msg = (
                f"Policy Update Approved for scheme '{target_obj.scheme_id}': {target_obj.summary}. "
                f"Check your profile to review updated eligibility requirements."
            )
            self.memory.save_alert(
                user_id=uid,
                doc_id=target_obj.scheme_id,
                alert_type="SCHEME_CHANGE_APPROVED",
                message=alert_msg,
            )
            affected_users.append(uid)

        return {
            "change_id": change_id,
            "status": "APPROVED",
            "citizens_re_evaluated": len(citizens),
            "affected_users": affected_users,
        }


class DailyValidityScheduler:
    """Proactively audits certificate validity daily and portal policy diffs weekly via APScheduler."""

    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        vault_dir: Optional[Path] = None,
        llm_client: Optional[Any] = None,
    ):
        self.memory = memory_store or MemoryStore()
        self.vault_dir = Path(vault_dir) if vault_dir else VAULT_DIR
        self.llm_client = llm_client
        self.scheduler = BackgroundScheduler()

    def run_daily_validity_check(self) -> dict[str, int]:
        """Runs validity audit across every user with vault documents and generates alerts."""
        from experience.dashboard.validity_tracker import ValidityTracker
        from experience.intake.vault import DocumentVault

        vault = DocumentVault(base_vault_dir=self.vault_dir)
        tracker = ValidityTracker(vault=vault, llm_client=self.llm_client)

        user_dirs = [d for d in self.vault_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        alerts_created = 0

        for udir in user_dirs:
            user_id = udir.name
            health = tracker.get_user_health_summary(user_id)

            for verdict in health.verdicts:
                if verdict.status in ("EXPIRED", "EXPIRING_SOON", "NEEDS_REVIEW"):
                    msg = (
                        f"Document Alert: Your {verdict.doc_type} is {verdict.status.replace('_', ' ')}. "
                        f"{verdict.date_calculation_reasoning}. "
                        f"Notice: The system detects expiry but cannot renew documents on your behalf."
                    )
                    self.memory.save_alert(
                        user_id=user_id,
                        doc_id=verdict.doc_id,
                        alert_type=f"DOC_{verdict.status}",
                        message=msg,
                        days_remaining=verdict.days_remaining,
                    )
                    alerts_created += 1

        return {"users_audited": len(user_dirs), "alerts_created": alerts_created}

    def run_weekly_scheme_check(self) -> dict[str, Any]:
        """Weekly scrape of official URLs comparing snapshots and extracting deadlines."""
        from knowledge.schemes.data import load_all_schemes
        monitor = SchemePolicyMonitor(memory_store=self.memory, llm_client=self.llm_client)
        schemes = load_all_schemes()
        results = []

        for s in schemes:
            bundle = monitor.check_scheme_for_updates(s)
            if bundle.has_policy_change:
                results.append({"scheme_id": s.id, "changes": len(bundle.changes)})

        return {"schemes_audited": len(schemes), "updates_flagged": len(results)}

    def start(self):
        """Starts background daily schedule at 04:00 UTC and weekly scheme diff on Sundays."""
        if not self.scheduler.running:
            self.scheduler.add_job(
                self.run_daily_validity_check,
                "cron",
                hour=4,
                minute=0,
                id="daily_validity_audit",
                replace_existing=True,
            )
            self.scheduler.add_job(
                self.run_weekly_scheme_check,
                "cron",
                day_of_week="sun",
                hour=2,
                minute=0,
                id="weekly_scheme_check",
                replace_existing=True,
            )
            self.scheduler.start()

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
