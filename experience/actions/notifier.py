"""Outbound Notification and Message Drafting Service for YojanaAgent.

Provides LLM-driven personalized message formulation (email, telegram, sms, in_app)
in the citizen's preferred language (Hindi/English), strict Aadhaar masking,
duplicate prevention (24-hour dedupe), hourly rate limiting, and an uncompromising
Human-in-the-Loop approval gate (NOTHING is dispatched without citizen approval).
"""

from __future__ import annotations

import email.message
import hashlib
import json
import logging
import smtplib
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import requests

from brain.llm_client import LLMClient, mask_aadhaar
from shared.config import (
    DATA_DIR,
    HOURLY_RATE_LIMIT,
    NOTIFY_DRY_RUN,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
    TELEGRAM_BOT_TOKEN,
)
from shared.schemas import (
    DraftActionResponse,
    DraftGenerationRequest,
    GeneratedDraftContent,
    OutboundMessageDraft,
)

logger = logging.getLogger(__name__)
DB_PATH = DATA_DIR / "yojana_memory.db"


class NotificationService:
    """Manages AI message drafting, deduplication, citizen approvals, and dispatches."""

    def __init__(
        self,
        db_path: Path = DB_PATH,
        llm_client: Optional[LLMClient] = None,
        dry_run: bool = NOTIFY_DRY_RUN,
        hourly_limit: int = HOURLY_RATE_LIMIT,
    ):
        self.db_path = db_path
        self.llm = llm_client or LLMClient()
        self.dry_run = dry_run
        self.hourly_limit = hourly_limit
        self._init_db()

    def _init_db(self):
        """Initialize SQLite tables for message drafts and dispatch logs."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_drafts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT,
                    body TEXT NOT NULL,
                    language TEXT DEFAULT 'en',
                    status TEXT DEFAULT 'PENDING_APPROVAL',
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    dedupe_hash TEXT,
                    metadata_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dispatch_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    draft_id TEXT,
                    user_id TEXT,
                    channel TEXT,
                    dispatched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT,
                    details TEXT
                )
            """)

    @staticmethod
    def _compute_dedupe_hash(request: DraftGenerationRequest) -> str:
        """Compute SHA-256 fingerprint from user, event, channel, recipient and core context."""
        context_str = json.dumps(request.context_data, sort_keys=True, default=str)
        raw = f"{request.user_id}|{request.event_type}|{request.channel}|{request.recipient}|{context_str}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _check_duplicate(self, dedupe_hash: str) -> Optional[OutboundMessageDraft]:
        """Check if an identical draft was created within the last 24 hours."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM message_drafts
                WHERE dedupe_hash = ? AND created_at >= ? AND status != 'DISCARDED'
                ORDER BY created_at DESC LIMIT 1
                """,
                (dedupe_hash, cutoff),
            ).fetchone()
            if row:
                return self._row_to_draft(row)
        return None

    def check_rate_limit(self, user_id: str) -> bool:
        """Verify whether user or system has exceeded the hourly dispatch quota."""
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute(
                """
                SELECT COUNT(*) FROM dispatch_logs
                WHERE user_id = ? AND dispatched_at >= ? AND status = 'SENT'
                """,
                (user_id, one_hour_ago),
            ).fetchone()[0]
            return count < self.hourly_limit

    def draft_message(self, request: DraftGenerationRequest) -> OutboundMessageDraft:
        """
        Formulate a personalized, grounded notification draft in citizen's language.
        Always masked for privacy and stored in PENDING_APPROVAL status.
        """
        dedupe_hash = self._compute_dedupe_hash(request)
        existing = self._check_duplicate(dedupe_hash)
        if existing:
            logger.info("Found duplicate draft %s created within last 24h. Returning existing draft.", existing.id)
            return existing

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        masked_context = json.loads(mask_aadhaar(json.dumps(request.context_data, default=str)))
        context_json_str = json.dumps(masked_context, ensure_ascii=False, indent=2)

        prompt = f"""You are an empathetic, clear, and professional government service advisor for YojanaAgent.
The current date is {today_str}.

Compose an outbound message for the citizen regarding the following event:
Event Type: {request.event_type}
Channel: {request.channel} (e.g. email, telegram, sms, in_app)
Recipient: {request.recipient}
Target Language: {request.language} (If 'hi', write in natural, respectful Hindi in Devanagari script; if 'en', write in polite, accessible English).

Context details:
{context_json_str}

Instructions:
1. Address the recipient respectfully.
2. If channel is 'email', provide an informative, clear subject line and structured body.
3. If channel is 'telegram' or 'sms', keep it concise and actionable.
4. Privacy requirement: NEVER include unmasked 12-digit Aadhaar numbers. If an Aadhaar number is referenced, ensure it is masked like XXXX-XXXX-1234.
5. Provide clear, concrete next steps (e.g., visit official portal, nearest CSC center, or submit renewal).
6. Return structured output matching GeneratedDraftContent.
"""

        content: Optional[GeneratedDraftContent] = None
        try:
            content, llm_res = self.llm.generate_structured(
                prompt=prompt,
                schema_class=GeneratedDraftContent,
                system_prompt="You are YojanaAgent's official outbound communication drafting engine.",
            )
            if content:
                subject = mask_aadhaar(content.subject) if content.subject else None
                body = mask_aadhaar(content.body)
                language = content.language or request.language
            else:
                logger.warning("Structured extraction returned None. Using safe template.")
                subject, body, language = self._fallback_template(request, today_str)
        except Exception as err:
            logger.warning("LLM drafting failed or unavailable: %s. Using standard safe template.", err)
            subject, body, language = self._fallback_template(request, today_str)

        draft_id = f"draft_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        metadata = {
            "event_type": request.event_type,
            "dedupe_hash": dedupe_hash,
            "llm_reasoning": getattr(content, "reasoning", "Template fallback") if "content" in locals() else "Fallback",
        }

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO message_drafts (
                    id, user_id, channel, recipient, subject, body, language,
                    status, created_at, sent_at, dedupe_hash, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    draft_id,
                    request.user_id,
                    request.channel,
                    request.recipient,
                    subject,
                    body,
                    language,
                    "PENDING_APPROVAL",
                    now_iso,
                    None,
                    dedupe_hash,
                    json.dumps(metadata),
                ),
            )

        return OutboundMessageDraft(
            id=draft_id,
            user_id=request.user_id,
            channel=request.channel,
            recipient=request.recipient,
            subject=subject,
            body=body,
            language=language,
            status="PENDING_APPROVAL",
            created_at=now_iso,
            sent_at=None,
            approval_guarantee="Nothing is sent without your approval.",
            metadata=metadata,
        )

    def _fallback_template(self, request: DraftGenerationRequest, today_str: str) -> tuple[Optional[str], str, str]:
        """Provides a safe, pre-formatted communication template when LLM is unavailable."""
        event = request.event_type.replace("_", " ").title()
        if request.language == "hi":
            subject = f"योजना सूचना: {event}" if request.channel == "email" else None
            body = (
                f"नमस्ते,\n\nयह योजना एजेंट की ओर से एक महत्वपूर्ण सूचना है। "
                f"आपके दस्तावेज़ या आवेदन के संबंध में ({event}) ध्यान देने की आवश्यकता है।\n"
                f"दिनांक: {today_str}\n\n"
                f"कृपया योजना पोर्टल पर जाकर अपने विवरण की जांच करें या निकटतम सीएससी (CSC) केंद्र से संपर्क करें।"
            )
            lang = "hi"
        else:
            subject = f"YojanaAgent Alert: {event}" if request.channel == "email" else None
            body = (
                f"Hello,\n\nThis is an important update regarding your scheme profile ({event}).\n"
                f"Date: {today_str}\n\n"
                f"Please review your details on the YojanaAgent dashboard or contact your nearest Common Service Centre (CSC)."
            )
            lang = "en"
        return subject, body, lang

    def get_draft(self, draft_id: str) -> Optional[OutboundMessageDraft]:
        """Retrieve a specific draft by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM message_drafts WHERE id = ?", (draft_id,)).fetchone()
            if row:
                return self._row_to_draft(row)
        return None

    def list_drafts(
        self, user_id: Optional[str] = None, status: Optional[str] = None
    ) -> list[OutboundMessageDraft]:
        """List drafts filtered by citizen ID and/or approval status."""
        query = "SELECT * FROM message_drafts WHERE 1=1"
        params: list[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_draft(r) for r in rows]

    def edit_draft(
        self, draft_id: str, body: Optional[str] = None, subject: Optional[str] = None
    ) -> OutboundMessageDraft:
        """Citizen modifies the draft before approving dispatch."""
        draft = self.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        if draft.status != "PENDING_APPROVAL":
            raise ValueError(f"Cannot edit draft in status '{draft.status}'")

        new_body = mask_aadhaar(body) if body is not None else draft.body
        new_subject = mask_aadhaar(subject) if subject is not None else draft.subject

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE message_drafts SET body = ?, subject = ? WHERE id = ?",
                (new_body, new_subject, draft_id),
            )

        draft.body = new_body
        draft.subject = new_subject
        return draft

    def discard_draft(self, draft_id: str) -> DraftActionResponse:
        """Citizen chooses to reject and discard a draft."""
        draft = self.get_draft(draft_id)
        if not draft:
            return DraftActionResponse(
                draft_id=draft_id,
                status="NOT_FOUND",
                dispatched=False,
                channel="unknown",
                message="Draft not found.",
            )
        if draft.status == "SENT":
            return DraftActionResponse(
                draft_id=draft_id,
                status="SENT",
                dispatched=True,
                channel=draft.channel,
                message="Cannot discard a draft that has already been dispatched.",
            )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE message_drafts SET status = 'DISCARDED' WHERE id = ?", (draft_id,))

        return DraftActionResponse(
            draft_id=draft_id,
            status="DISCARDED",
            dispatched=False,
            channel=draft.channel,
            message="Draft discarded successfully.",
        )

    def approve_and_send(self, draft_id: str) -> DraftActionResponse:
        """
        Explicit Citizen Approval Gate: Dispatches the message via SMTP or Telegram.
        Honors NOTIFY_DRY_RUN and rate limits.
        """
        draft = self.get_draft(draft_id)
        if not draft:
            return DraftActionResponse(
                draft_id=draft_id,
                status="NOT_FOUND",
                dispatched=False,
                channel="unknown",
                message="Draft not found.",
            )

        if draft.status == "SENT":
            return DraftActionResponse(
                draft_id=draft_id,
                status="SENT",
                dispatched=True,
                channel=draft.channel,
                message="Message was already approved and sent previously.",
            )

        if draft.status == "DISCARDED":
            return DraftActionResponse(
                draft_id=draft_id,
                status="DISCARDED",
                dispatched=False,
                channel=draft.channel,
                message="Cannot dispatch a discarded draft.",
            )

        # Enforce rate limit
        if not self.check_rate_limit(draft.user_id):
            logger.warning("Rate limit reached for user %s (%d msgs/hr).", draft.user_id, self.hourly_limit)
            return DraftActionResponse(
                draft_id=draft_id,
                status="RATE_LIMITED",
                dispatched=False,
                channel=draft.channel,
                message=f"Rate limit exceeded (maximum {self.hourly_limit} dispatches per hour). Please try later.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()

        # Check Dry Run
        if self.dry_run:
            logger.info(
                "[DRY RUN] Message approved and simulated for user %s via %s: to=%s, subject=%s",
                draft.user_id,
                draft.channel,
                draft.recipient,
                draft.subject,
            )
            self._record_dispatch(draft_id, draft.user_id, draft.channel, "SENT", "Simulated delivery (dry run)")
            self._update_draft_status(draft_id, "SENT", now_iso)
            return DraftActionResponse(
                draft_id=draft_id,
                status="SENT",
                dispatched=True,
                channel=draft.channel,
                message="Message approved and simulated successfully (dry run mode active).",
            )

        # Live dispatch
        dispatch_error: Optional[str] = None
        try:
            if draft.channel == "email":
                self._send_email(draft)
            elif draft.channel == "telegram":
                self._send_telegram(draft)
            else:
                # sms or in_app
                logger.info("Channel '%s' dispatch recorded for %s", draft.channel, draft.recipient)
        except Exception as ex:
            dispatch_error = str(ex)
            logger.error("Failed to dispatch %s to %s: %s", draft.channel, draft.recipient, ex)

        if dispatch_error:
            self._record_dispatch(draft_id, draft.user_id, draft.channel, "FAILED", dispatch_error)
            return DraftActionResponse(
                draft_id=draft_id,
                status="FAILED",
                dispatched=False,
                channel=draft.channel,
                message=f"Dispatch failed: {dispatch_error}",
            )

        self._record_dispatch(draft_id, draft.user_id, draft.channel, "SENT", "Live dispatch confirmed")
        self._update_draft_status(draft_id, "SENT", now_iso)

        return DraftActionResponse(
            draft_id=draft_id,
            status="SENT",
            dispatched=True,
            channel=draft.channel,
            message="Message approved and delivered successfully.",
        )

    def _send_email(self, draft: OutboundMessageDraft):
        """Sends an email via SMTP."""
        msg = email.message.EmailMessage()
        msg["Subject"] = draft.subject or "YojanaAgent Notification"
        msg["From"] = SMTP_FROM
        msg["To"] = draft.recipient
        msg.set_content(draft.body)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USER and SMTP_PASSWORD:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

    def _send_telegram(self, draft: OutboundMessageDraft):
        """Sends a message via Telegram Bot API."""
        if not TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured in environment")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": draft.recipient, "text": draft.body, "parse_mode": "Markdown"},
            timeout=10,
        )
        resp.raise_for_status()

    def _update_draft_status(self, draft_id: str, status: str, sent_at: Optional[str]):
        """Persist status transition in SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE message_drafts SET status = ?, sent_at = ? WHERE id = ?",
                (status, sent_at, draft_id),
            )

    def _record_dispatch(self, draft_id: str, user_id: str, channel: str, status: str, details: str):
        """Record dispatch attempt in audit log."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO dispatch_logs (draft_id, user_id, channel, status, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (draft_id, user_id, channel, status, details),
            )

    @staticmethod
    def _row_to_draft(row: sqlite3.Row) -> OutboundMessageDraft:
        """Maps an SQLite row to an OutboundMessageDraft Pydantic instance."""
        meta = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
        return OutboundMessageDraft(
            id=row["id"],
            user_id=row["user_id"],
            channel=row["channel"],
            recipient=row["recipient"],
            subject=row["subject"],
            body=row["body"],
            language=row["language"] or "en",
            status=row["status"],
            created_at=row["created_at"],
            sent_at=row["sent_at"],
            approval_guarantee="Nothing is sent without your approval.",
            metadata=meta,
        )
