"""Unit tests for Phase 4: Notification and Outbound Message Drafts.

Tests message drafting (English/Hindi), Aadhaar masking, human-in-the-loop approval gate,
24-hour deduplication, rate limiting, and dry-run dispatch.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from brain.llm_client import LLMClient, LLMResult
from experience.actions.notifier import NotificationService
from shared.schemas import (
    DraftGenerationRequest,
    GeneratedDraftContent,
    OutboundMessageDraft,
)


@pytest.fixture
def mock_llm_client():
    client = MagicMock(spec=LLMClient)
    return client


def test_draft_message_with_mocked_llm(tmp_path: Path, mock_llm_client):
    """Test AI message drafting with Aadhaar masking and PENDING_APPROVAL status."""
    db_file = tmp_path / "test_notifier.db"
    mock_content = GeneratedDraftContent(
        subject="Urgent: Income Certificate Renewal Required",
        body="Dear Citizen, your income certificate associated with Aadhaar 1234 5678 9012 is expiring in 15 days.",
        language="en",
        reasoning="Polite reminder with actionable renewal guidance.",
    )
    mock_llm_client.generate_structured.return_value = (
        mock_content,
        LLMResult(
            ok=True,
            text="",
            error=None,
            provider="gemini",
        ),
    )

    service = NotificationService(db_path=db_file, llm_client=mock_llm_client, dry_run=True)

    request = DraftGenerationRequest(
        user_id="citizen_101",
        event_type="DOCUMENT_EXPIRY",
        recipient="citizen@example.com",
        channel="email",
        language="en",
        context_data={"doc_type": "Income Certificate", "aadhaar_raw": "1234 5678 9012"},
    )

    draft = service.draft_message(request)

    assert draft.status == "PENDING_APPROVAL"
    assert draft.user_id == "citizen_101"
    assert draft.channel == "email"
    assert draft.approval_guarantee == "Nothing is sent without your approval."
    # Verify Aadhaar is masked in the body
    assert "1234 5678 9012" not in draft.body
    assert "XXXX-XXXX-9012" in draft.body


def test_draft_deduplication(tmp_path: Path, mock_llm_client):
    """Test that duplicate requests within 24 hours reuse the existing draft."""
    db_file = tmp_path / "test_notifier.db"
    mock_content = GeneratedDraftContent(
        subject="Deadline Reminder: PM-Kisan",
        body="Reminder: The deadline for PM-Kisan e-KYC is approaching.",
        language="en",
    )
    mock_llm_client.generate_structured.return_value = (
        mock_content,
        LLMResult(
            ok=True,
            text="",
            error=None,
            provider="gemini",
        ),
    )

    service = NotificationService(db_path=db_file, llm_client=mock_llm_client, dry_run=True)

    request = DraftGenerationRequest(
        user_id="citizen_102",
        event_type="DEADLINE_REMINDER",
        recipient="farmer@example.com",
        channel="email",
        language="en",
        context_data={"scheme_id": "pm_kisan"},
    )

    draft_1 = service.draft_message(request)
    draft_2 = service.draft_message(request)

    # Identical draft should be returned without second generation
    assert draft_1.id == draft_2.id
    assert mock_llm_client.generate_structured.call_count == 1


def test_edit_and_discard_draft(tmp_path: Path):
    """Test citizen modifying text and discarding drafts."""
    db_file = tmp_path / "test_notifier.db"
    service = NotificationService(
        db_path=db_file,
        llm_client=LLMClient(google_key="", anthropic_key=""),
        dry_run=True,
    )

    request = DraftGenerationRequest(
        user_id="citizen_103",
        event_type="CSC_APPOINTMENT",
        recipient="citizen@example.com",
        channel="email",
        language="en",
        context_data={"center": "Tehsil Center"},
    )

    draft = service.draft_message(request)
    assert draft.status == "PENDING_APPROVAL"

    # Edit draft
    edited = service.edit_draft(draft.id, body="Updated appointment reminder at 10 AM.", subject="Updated CSC Notice")
    assert edited.body == "Updated appointment reminder at 10 AM."
    assert edited.subject == "Updated CSC Notice"

    # Discard draft
    discard_res = service.discard_draft(draft.id)
    assert discard_res.status == "DISCARDED"

    retrieved = service.get_draft(draft.id)
    assert retrieved.status == "DISCARDED"

    # Attempting to send a discarded draft should fail
    action_res = service.approve_and_send(draft.id)
    assert action_res.status == "DISCARDED"
    assert action_res.dispatched is False


def test_approve_and_send_dry_run(tmp_path: Path):
    """Test human-in-the-loop approval and simulated dispatch."""
    db_file = tmp_path / "test_notifier.db"
    service = NotificationService(
        db_path=db_file,
        llm_client=LLMClient(google_key="", anthropic_key=""),
        dry_run=True,
    )

    request = DraftGenerationRequest(
        user_id="citizen_104",
        event_type="SCHEME_UPDATE",
        recipient="user@example.com",
        channel="email",
        language="en",
        context_data={"scheme_name": "PMAY"},
    )

    draft = service.draft_message(request)
    assert draft.status == "PENDING_APPROVAL"

    # Approve and send
    result = service.approve_and_send(draft.id)
    assert result.status == "SENT"
    assert result.dispatched is True

    # Check updated draft in database
    sent_draft = service.get_draft(draft.id)
    assert sent_draft.status == "SENT"
    assert sent_draft.sent_at is not None

    # Idempotent re-send check
    re_result = service.approve_and_send(draft.id)
    assert re_result.status == "SENT"
    assert "already approved" in re_result.message


def test_rate_limiting(tmp_path: Path):
    """Test hourly dispatch rate limiting."""
    db_file = tmp_path / "test_notifier.db"
    # Set limit to 2 messages per hour for testing
    service = NotificationService(
        db_path=db_file,
        llm_client=LLMClient(google_key="", anthropic_key=""),
        dry_run=True,
        hourly_limit=2,
    )

    for i in range(2):
        req = DraftGenerationRequest(
            user_id="citizen_rate_test",
            event_type=f"ALERT_{i}",
            recipient="test@example.com",
            channel="email",
            context_data={"index": i},
        )
        d = service.draft_message(req)
        res = service.approve_and_send(d.id)
        assert res.status == "SENT"

    # Third send should exceed the limit
    req_3 = DraftGenerationRequest(
        user_id="citizen_rate_test",
        event_type="ALERT_3",
        recipient="test@example.com",
        channel="email",
        context_data={"index": 3},
    )
    d3 = service.draft_message(req_3)
    res_3 = service.approve_and_send(d3.id)

    assert res_3.status == "RATE_LIMITED"
    assert res_3.dispatched is False
    assert "Rate limit exceeded" in res_3.message


def test_hindi_fallback_drafting(tmp_path: Path):
    """Test fallback template generation in Hindi when offline."""
    db_file = tmp_path / "test_notifier.db"
    offline_client = LLMClient(google_key="", anthropic_key="")
    service = NotificationService(db_path=db_file, llm_client=offline_client, dry_run=True)

    request = DraftGenerationRequest(
        user_id="citizen_hindi_01",
        event_type="DOCUMENT_EXPIRY",
        recipient="+919876543210",
        channel="sms",
        language="hi",
        context_data={"doc_type": "जाति प्रमाण पत्र"},
    )

    draft = service.draft_message(request)
    assert draft.language == "hi"
    assert "योजना एजेंट" in draft.body
    assert draft.status == "PENDING_APPROVAL"
