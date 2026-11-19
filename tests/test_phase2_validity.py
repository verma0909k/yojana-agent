"""Unit tests for Phase 2: Validity Tracking, Date Arithmetic Reasoning,
Two-Pass Reviewer Audit, Affected Application Mapping, and APScheduler Daily Jobs.
All LLM calls are mocked so pytest runs offline without network dependency.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from brain.llm_client import LLMClient, LLMResult
from experience.dashboard.application_tracker import ApplicationTracker
from experience.dashboard.validity_tracker import ValidityTracker
from experience.intake.vault import DocumentVault
from knowledge.monitor import DailyValidityScheduler, MemoryStore
from shared.schemas import (
    DocumentExtraction,
    DocumentHealthSummary,
    DocumentValidityVerdict,
    ReviewerAuditResult,
    StoredDocumentMetadata,
)


def test_validity_evaluation_with_injected_date():
    """Verify that current date is injected and date arithmetic reasoning is produced."""
    client = LLMClient(google_key="mock", gemini_model="mock")
    tracker = ValidityTracker(llm_client=client)

    doc = StoredDocumentMetadata(
        doc_id="doc_income_101",
        user_id="citizen_42",
        filename="income.pdf",
        doc_type="Income Certificate",
        holder_name="Ananya Verma",
        issue_date="2025-01-15",
        expiry_date="2026-01-14",
        created_at="2025-01-15T00:00:00Z",
        file_path="/dummy/income.enc",
    )

    injected_today = "2026-03-01"

    mock_verdict = DocumentValidityVerdict(
        doc_id="doc_income_101",
        doc_type="Income Certificate",
        status="EXPIRED",
        expiry_date="2026-01-14",
        days_remaining=-46,
        date_calculation_reasoning="Today is 2026-03-01. Expiry was 2026-01-14. 46 days past expiry.",
        confidence=0.98,
        affected_applications=["App #app_01 for 'National Scholarship Portal'"],
        renewal_steps=[
            "Visit Tehsil office with previous certificate copy.",
            "Submit Parivar Pehchan Patra and electricity bill.",
            "Download digitally signed renewed income certificate in 7 days.",
        ],
    )

    mock_audit = ReviewerAuditResult(
        agrees=True,
        reason="Calculations verified against Haryana 1-year revenue certificate validity guidelines.",
        audit_confidence=0.99,
    )

    with patch.object(client, "generate_structured", side_effect=[
        (mock_verdict, LLMResult(ok=True, text="{}")),
        (mock_audit, LLMResult(ok=True, text="{}")),
    ]):
        verdict = tracker.evaluate_document_validity(
            doc=doc,
            active_apps=[{"task_id": "app_01", "scheme_name": "National Scholarship Portal", "status": "DRAFT", "documents_ready": ["doc_income_101"]}],
            current_date_iso=injected_today,
        )

        assert verdict.status == "EXPIRED"
        assert verdict.days_remaining == -46
        assert "46 days past expiry" in verdict.date_calculation_reasoning
        assert len(verdict.affected_applications) >= 1
        assert "cannot renew documents on your behalf" in verdict.regulatory_disclaimer or "must renew the document yourself" in verdict.regulatory_disclaimer


def test_reviewer_disagreement_flags_needs_review():
    """Verify that when the Reviewer disagrees or confidence is low, the status becomes NEEDS_REVIEW."""
    client = LLMClient(google_key="mock", gemini_model="mock")
    tracker = ValidityTracker(llm_client=client)

    doc = StoredDocumentMetadata(
        doc_id="doc_obc_202",
        user_id="citizen_42",
        filename="obc.pdf",
        doc_type="OBC Certificate",
        holder_name="Rahul",
        issue_date="2025-03-01",
        created_at="2025-03-01T00:00:00Z",
        file_path="/dummy/obc.enc",
    )

    primary_verdict = DocumentValidityVerdict(
        doc_id="doc_obc_202",
        doc_type="OBC Certificate",
        status="VALID",
        expiry_date="2028-03-01",
        days_remaining=730,
        date_calculation_reasoning="OBC certificate treated as valid for 3 years.",
        confidence=0.95,
        renewal_steps=["Apply online"],
    )

    # Reviewer catches that OBC Non-Creamy Layer is valid for only 1 financial year, not 3 years!
    reviewer_disagree = ReviewerAuditResult(
        agrees=False,
        reason="OBC Non-Creamy Layer certificates expire at the end of the financial year (March 31) under DoPT guidelines. 3-year claim is incorrect.",
        audit_confidence=0.95,
    )

    with patch.object(client, "generate_structured", side_effect=[
        (primary_verdict, LLMResult(ok=True, text="{}")),
        (reviewer_disagree, LLMResult(ok=True, text="{}")),
    ]):
        verdict = tracker.evaluate_document_validity(
            doc=doc,
            active_apps=[],
            current_date_iso="2026-03-01",
        )

        # Must be marked NEEDS_REVIEW because Reviewer disagreed
        assert verdict.status == "NEEDS_REVIEW"
        assert verdict.needs_review is True
        assert "Reviewer audit flagged discrepancy" in verdict.review_reason


def test_document_health_summary_with_disclaimer(tmp_path: Path):
    """Verify health summary computes valid percentage and includes the mandated regulatory disclaimer."""
    vault = DocumentVault(base_vault_dir=tmp_path / "vault")
    user_id = "user_health_1"

    # Save 2 documents: 1 valid, 1 expired
    vault.save_document(
        user_id=user_id,
        file_bytes=b"aadhaar-bytes",
        filename="aadhaar.jpg",
        extraction=DocumentExtraction(doc_type="Aadhaar Card", holder_name="Citizen One"),
    )
    vault.save_document(
        user_id=user_id,
        file_bytes=b"income-bytes",
        filename="income.pdf",
        extraction=DocumentExtraction(doc_type="Income Certificate", holder_name="Citizen One", expiry_date="2025-01-01"),
    )

    offline_client = LLMClient(google_key="", anthropic_key="")
    tracker = ValidityTracker(vault=vault, llm_client=offline_client)
    summary = tracker.get_user_health_summary(user_id=user_id, current_date_iso="2026-03-01")

    assert summary.total_documents == 2
    assert "cannot renew documents on your behalf" in summary.disclaimer
    assert len(summary.verdicts) == 2


def test_apscheduler_daily_job_alerts(tmp_path: Path):
    """Verify daily scheduler processes user vault and persists alerts in SQLite."""
    vault_dir = tmp_path / "vault"
    db_file = tmp_path / "test_memory.db"
    mem_store = MemoryStore(db_path=db_file)

    vault = DocumentVault(base_vault_dir=vault_dir)
    user_id = "citizen_scheduled_7"

    # Save an expired certificate
    vault.save_document(
        user_id=user_id,
        file_bytes=b"expired-cert",
        filename="old_cert.pdf",
        extraction=DocumentExtraction(doc_type="OBC Certificate", expiry_date="2025-01-01"),
    )

    offline_client = LLMClient(google_key="", anthropic_key="")
    scheduler = DailyValidityScheduler(memory_store=mem_store, vault_dir=vault_dir, llm_client=offline_client)

    # Trigger audit run
    res = scheduler.run_daily_validity_check()
    assert res["users_audited"] >= 1
    assert res["alerts_created"] >= 1

    alerts = mem_store.get_alerts(user_id)
    assert len(alerts) >= 1
    assert "cannot renew documents on your behalf" in alerts[0]["message"]

    # Verify scheduler starts and stops cleanly
    scheduler.start()
    assert scheduler.scheduler.running is True
    scheduler.stop()
    assert scheduler.scheduler.running is False
