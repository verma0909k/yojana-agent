"""Unit tests for Phase 3: Scheme Policy Monitor, Official Portal Diff Scraping,
Grounded LLM Change Summaries, Deadline Extraction with Source Quotes,
and Citizen Re-Evaluation upon Change Approval.
All LLM and network calls are mocked so pytest runs offline without network dependency.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import requests
from brain.llm_client import LLMClient, LLMResult
from knowledge.monitor import (
    MemoryStore,
    SchemePolicyMonitor,
    fetch_portal_text,
)
from shared.schemas import (
    CitizenProfile,
    ExtractedDeadline,
    Fact,
    ReviewerAuditResult,
    Scheme,
    SchemeChangeSummary,
    SchemeExtractionBundle,
)


def test_portal_fetch_network_resilience():
    """Verify that network timeouts and HTTP errors return None gracefully and never count as changes."""
    # Invalid URL returns None
    assert fetch_portal_text("") is None
    assert fetch_portal_text("not_a_url") is None

    # Mock timeout exception
    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
        res = fetch_portal_text("https://pmkisan.gov.in")
        assert res is None

    # Mock HTTP 503 Service Unavailable
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    with patch("requests.get", return_value=mock_resp):
        res = fetch_portal_text("https://pmkisan.gov.in")
        assert res is None

    # Mock clean HTML stripping
    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_ok.text = "<html><body><h1>PM Kisan</h1><p>Under PM Kisan, eligible farmers get Rs 6000 per year.</p><script>console.log('ad')</script></body></html>"
    with patch("requests.get", return_value=mock_ok):
        text = fetch_portal_text("https://pmkisan.gov.in")
        assert text is not None
        assert "eligible farmers get Rs 6000 per year" in text
        assert "console.log" not in text


def test_scheme_change_detection_and_needs_review(tmp_path: Path):
    """Verify LLM compares portal diffs, requires evidence quotes, and saves strictly as NEEDS_REVIEW."""
    db_file = tmp_path / "test_memory.db"
    mem_store = MemoryStore(db_path=db_file)
    client = LLMClient(google_key="mock", gemini_model="mock")
    monitor = SchemePolicyMonitor(memory_store=mem_store, llm_client=client)

    scheme = Scheme(
        id="nsp-scholarship",
        name="National Scholarship Portal",
        ministry="Ministry of Education",
        description="Scholarship scheme",
        benefits="Up to Rs 20,000",
        official_url="https://scholarships.gov.in",
    )

    # 1. Baseline snapshot
    baseline_text = "National Scholarship Portal: Family annual income limit is Rs 2,50,000 for regular students."
    mem_store.save_scheme_snapshot(scheme.id, baseline_text)

    # 2. Updated portal text: Income limit raised to Rs 3,00,000
    new_text = "National Scholarship Portal: Family annual income limit is revised to Rs 3,00,000 for all eligible students. Last date: 31 March 2026."

    mock_change = SchemeChangeSummary(
        id="chg_01",
        scheme_id=scheme.id,
        summary="Family annual income limit raised from Rs 2.5L to Rs 3.0L",
        before="Family annual income limit is Rs 2,50,000",
        after="Family annual income limit is revised to Rs 3,00,000",
        confidence=0.98,
        detected_on="2026-03-01",
        status="NEEDS_REVIEW",
        evidence_quotes=["Family annual income limit is revised to Rs 3,00,000"],
    )

    mock_deadline = ExtractedDeadline(
        id="dl_01",
        scheme_id=scheme.id,
        stage="Fresh Applications Close",
        date_str="2026-03-31",
        source_quote="Last date: 31 March 2026",
        days_remaining=30,
        status="closing_soon",
        extracted_on="2026-03-01",
    )

    mock_bundle = SchemeExtractionBundle(
        changes=[mock_change],
        deadlines=[mock_deadline],
        has_policy_change=True,
    )

    mock_audit = ReviewerAuditResult(
        agrees=True,
        reason="Revamped income threshold quote verified against source text.",
        audit_confidence=0.97,
    )

    with patch.object(client, "generate_structured", side_effect=[
        (mock_bundle, LLMResult(ok=True, text="{}")),
        (mock_audit, LLMResult(ok=True, text="{}")),
    ]):
        bundle = monitor.check_scheme_for_updates(
            scheme=scheme,
            current_date_iso="2026-03-01",
            fetched_text_override=new_text,
        )

        assert bundle.has_policy_change is True
        assert len(bundle.changes) == 1
        assert bundle.changes[0].status == "NEEDS_REVIEW"
        assert len(bundle.changes[0].evidence_quotes) >= 1
        assert "revised to Rs 3,00,000" in bundle.changes[0].evidence_quotes[0]

        # Verify saved in SQLite database as NEEDS_REVIEW
        saved_updates = mem_store.get_scheme_updates(scheme_id=scheme.id)
        assert len(saved_updates) == 1
        assert saved_updates[0]["status"] == "NEEDS_REVIEW"
        assert saved_updates[0]["summary"] == "Family annual income limit raised from Rs 2.5L to Rs 3.0L"

        # Verify deadline saved with source quote
        saved_deadlines = mem_store.get_deadlines(scheme_id=scheme.id)
        assert len(saved_deadlines) >= 1
        assert saved_deadlines[0]["source_quote"] == "Last date: 31 March 2026"


def test_approve_scheme_change_reevaluates_citizens(tmp_path: Path):
    """Verify approving a scheme change marks it APPROVED and generates alerts for saved citizens."""
    db_file = tmp_path / "test_memory.db"
    mem_store = MemoryStore(db_path=db_file)
    client = LLMClient(google_key="mock", gemini_model="mock")
    monitor = SchemePolicyMonitor(memory_store=mem_store, llm_client=client)

    # 1. Save a citizen profile in SQLite
    user_id = "citizen_student_9"
    profile = CitizenProfile(
        annual_income=Fact(value=280000, confidence=1.0),
    )
    mem_store.save_profile(user_id, profile)

    # 2. Insert a detected change in NEEDS_REVIEW status
    chg = SchemeChangeSummary(
        id="chg_nsp_income_raise",
        scheme_id="nsp-scholarship",
        summary="Income limit raised to Rs 3,00,000",
        before="2,50,000",
        after="3,00,000",
        confidence=0.99,
        detected_on="2026-03-01",
        status="NEEDS_REVIEW",
        evidence_quotes=["revised to Rs 3,00,000"],
    )
    mem_store.save_scheme_update(chg)

    # 3. Approve the scheme change
    result = monitor.approve_scheme_change("chg_nsp_income_raise")
    assert result["status"] == "APPROVED"
    assert result["citizens_re_evaluated"] == 1
    assert user_id in result["affected_users"]

    # 4. Verify update status in DB is now APPROVED
    updates = mem_store.get_scheme_updates(status="APPROVED")
    assert len(updates) == 1
    assert updates[0]["id"] == "chg_nsp_income_raise"

    # 5. Verify alert generated for the citizen
    alerts = mem_store.get_alerts(user_id)
    assert len(alerts) >= 1
    assert alerts[0]["alert_type"] == "SCHEME_CHANGE_APPROVED"
    assert "Policy Update Approved" in alerts[0]["message"]
