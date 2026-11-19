"""Unit tests for Phase 6: FastAPI Route Functions, X-User-Id Dependency Scoping,
Vault Management, Scheme Intelligence, Outbound Notifications, and Right-to-Erasure.
Directly unit tests endpoint functions for offline execution within sandbox.
"""

import asyncio
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.datastructures import UploadFile

from brain.api import (
    approve_draft,
    audit_consistency,
    discard_draft,
    explain_scheme_rejection,
    get_current_user_id,
    get_vault_health,
    health_check,
    list_documents,
    list_drafts,
    list_scheme_updates,
    list_upcoming_deadlines,
    upload_document,
    wipe_citizen_data,
)
from brain.llm_client import LLMResult
from experience.actions.notifier import NotificationService
from knowledge.monitor import MemoryStore
from shared.schemas import (
    CitizenProfile,
    DocumentExtraction,
    DraftGenerationRequest,
    Fact,
    FieldConfidence,
    RejectionExplanation,
)


@pytest.fixture(autouse=True)
def mock_all_llm_calls():
    """Ensure all tests run completely offline without waiting for network timeouts."""
    with patch("brain.llm_client.LLMClient.generate_structured") as mock_struct, \
         patch("brain.llm_client.LLMClient.generate") as mock_gen:
        mock_struct.return_value = (None, LLMResult(ok=False, text="", error="Offline test mock", provider="mock"))
        mock_gen.return_value = LLMResult(ok=False, text="", error="Offline test mock", provider="mock")
        yield


def test_api_health_check():
    """Test health check returns system status and regulatory disclaimer."""
    data = health_check()
    assert data["status"] == "ok"
    assert "cannot renew documents on your behalf" in data["regulatory_disclaimer"]


def test_get_current_user_id_dependency():
    """Test X-User-Id extraction, sanitization, and default fallback."""
    assert get_current_user_id("citizen_123") == "citizen_123"
    assert get_current_user_id("user@test#1") == "usertest1"
    assert get_current_user_id(None) == "default_citizen"
    assert get_current_user_id("") == "default_citizen"


def test_vault_upload_and_list_endpoints():
    """Test document upload, encryption, and scoped listing via API function."""
    mock_extraction = DocumentExtraction(
        doc_type="Aadhaar Card",
        holder_name="Sunita Sharma",
        id_last4="4321",
        issue_date="2022-01-10",
        per_field_confidence=[FieldConfidence(field_name="holder_name", confidence=0.98)],
    )

    with patch("experience.intake.doc_extractor.DocumentExtractor.extract_from_image", return_value=mock_extraction):
        fake_file = UploadFile(
            file=io.BytesIO(b"fake_aadhaar_image_content"),
            filename="aadhaar.jpg",
            headers={"content-type": "image/jpeg"},
        )
        # Upload endpoint
        meta = upload_document(file=fake_file, user_id="citizen_api_test")
        assert meta.user_id == "citizen_api_test"
        assert meta.doc_type == "Aadhaar Card"
        assert meta.id_last4 == "4321"

        # List documents
        docs = list_documents(user_id="citizen_api_test")
        assert len(docs) >= 1
        assert any(d.doc_type == "Aadhaar Card" for d in docs)


def test_vault_health_and_consistency_endpoints():
    """Test vault health summary and cross-document consistency endpoint functions."""
    health = get_vault_health(user_id="citizen_api_test")
    assert "cannot renew documents" in health.disclaimer

    consistency = audit_consistency(user_id="citizen_api_test")
    assert isinstance(consistency.is_consistent, bool)
    assert isinstance(consistency.issues, list)


def test_scheme_updates_and_deadlines_endpoints():
    """Test scheme update diffs and extracted deadline endpoints."""
    updates = list_scheme_updates(status=None)
    assert isinstance(updates, list)

    deadlines = list_upcoming_deadlines()
    assert isinstance(deadlines, list)


def test_explain_rejection_endpoint():
    """Test explain rejection endpoint with grounded explanation."""
    mock_explanation = RejectionExplanation(
        scheme_id="pm-kisan",
        scheme_name="PM Kisan Samman Nidhi",
        plain_language_reason="PM-Kisan requires ownership of cultivable agricultural land, which is not verified.",
        blocking_criteria=["Agricultural landholding requirement"],
        evidence_quote="Small and marginal landholder farmer families with cultivable land.",
        suggested_next_steps=["Upload a verified Khasra-Khatauni land record."],
        alternative_schemes=["pmmy-mudra"],
    )

    with patch("knowledge.llm_matcher.LLMMatcher.explain_rejection", return_value=mock_explanation):
        data = explain_scheme_rejection(
            scheme_id="pm-kisan",
            language="en",
            user_id="citizen_api_test",
        )
        assert data.scheme_id == "pm-kisan"
        assert "cultivable agricultural land" in data.plain_language_reason
        assert len(data.suggested_next_steps) > 0


def test_drafts_approve_and_discard_endpoints():
    """Test outbound drafts listing, human-in-the-loop approval, and discard."""
    notifier = NotificationService()

    # Create a draft
    req = DraftGenerationRequest(
        user_id="citizen_api_drafts",
        event_type="DOCUMENT_EXPIRY",
        recipient="sunita@example.com",
        channel="email",
        language="en",
        context_data={"doc_type": "Income Certificate"},
    )
    draft = notifier.draft_message(req)

    # List drafts
    drafts = list_drafts(user_id="citizen_api_drafts")
    assert any(d.id == draft.id for d in drafts)

    # Approve draft
    appr_data = approve_draft(draft_id=draft.id, user_id="citizen_api_drafts")
    assert appr_data.status == "SENT"
    assert appr_data.dispatched is True

    # Create second draft to discard
    req2 = DraftGenerationRequest(
        user_id="citizen_api_drafts",
        event_type="CSC_APPOINTMENT",
        recipient="sunita@example.com",
        channel="email",
        language="en",
        context_data={"center": "CSC Center 1"},
    )
    draft2 = notifier.draft_message(req2)
    disc_data = discard_draft(draft_id=draft2.id, user_id="citizen_api_drafts")
    assert disc_data.status == "DISCARDED"


def test_right_to_erasure_endpoint():
    """Test DELETE /me/data permanently wiping citizen vault and database records."""
    store = MemoryStore()
    profile = CitizenProfile()
    profile.annual_income = Fact(value=200000, known=True)
    store.save_profile("citizen_to_erase", profile)

    # Verify profile exists
    assert store.get_profile("citizen_to_erase") is not None

    # Call wipe endpoint
    erasure = wipe_citizen_data(user_id="citizen_to_erase")
    assert erasure.status == "success"
    assert erasure.user_id == "citizen_to_erase"
    assert "permanently erased" in erasure.message

    # Verify profile was purged
    assert store.get_profile("citizen_to_erase") is None
