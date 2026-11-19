"""Unit tests for Phase 1: Document Vault, Vision Extraction, Aadhaar Masking,
Fernet Encryption, Scheme Linkage, and Evidentiary Consistency Auditing.
All LLM calls are mocked so pytest runs offline without network dependency.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from brain.llm_client import LLMClient, LLMResult, LLMCache, mask_aadhaar
from experience.intake.vault import DocumentVault
from experience.intake.doc_extractor import DocumentExtractor, LinkedSchemesResult
from shared.schemas import (
    CitizenProfile,
    ConsistencyIssue,
    DocumentConsistencyReport,
    DocumentExtraction,
    Fact,
    FieldConfidence,
    Scheme,
    StoredDocumentMetadata,
)


def test_aadhaar_masking():
    """Verify Aadhaar numbers are masked to the last 4 digits in various formats."""
    # Continuous 12 digits
    text1 = "My Aadhaar is 987654321098 and phone is 9876543210"
    masked1 = mask_aadhaar(text1)
    assert "XXXX-XXXX-1098" in masked1
    assert "987654321098" not in masked1

    # Spaced 12 digits: 1234 5678 9012
    text2 = "UIDAI: 1234 5678 9012 issued in 2021"
    masked2 = mask_aadhaar(text2)
    assert "XXXX-XXXX-9012" in masked2
    assert "1234 5678 9012" not in masked2

    # Hyphenated: 1234-5678-9012
    text3 = "Aadhaar Ref: 1234-5678-9012"
    masked3 = mask_aadhaar(text3)
    assert "XXXX-XXXX-9012" in masked3


def test_llm_cache(tmp_path: Path):
    """Verify SQLite caching stores and retrieves responses by prompt hash."""
    cache_db = tmp_path / "test_cache.db"
    cache = LLMCache(db_path=cache_db)

    h = "test_prompt_hash_123"
    assert cache.get(h) is None

    cache.set(h, "gemini", "gemini-2.0-flash", "Cached response content")
    assert cache.get(h) == "Cached response content"


def test_fernet_vault_storage(tmp_path: Path):
    """Verify documents stored in data/vault/<user_id>/ are strongly encrypted on disk and decrypted accurately."""
    vault = DocumentVault(base_vault_dir=tmp_path)
    user_id = "user_test_99"

    raw_content = b"Official Income Certificate issued by Tehsildar Rohtak for Rs 1,80,000"
    extraction = DocumentExtraction(
        doc_type="Income Certificate",
        holder_name="Ananya Verma",
        issue_date="2026-01-15",
        expiry_date="2027-01-14",
        income_amount=180000,
        id_last4="4321",
        per_field_confidence=[
            FieldConfidence(field_name="income_amount", confidence=0.98, value_str="180000"),
            FieldConfidence(field_name="holder_name", confidence=0.99, value_str="Ananya Verma"),
        ],
    )

    # 1. Save document
    meta = vault.save_document(
        user_id=user_id,
        file_bytes=raw_content,
        filename="income_cert.pdf",
        extraction=extraction,
        mime_type="application/pdf",
        linked_scheme_ids=["nsp-scholarship"],
    )

    assert meta.user_id == user_id
    assert meta.doc_type == "Income Certificate"
    assert meta.id_last4 == "4321"

    # 2. Verify on-disk file is encrypted and does NOT contain raw plaintext
    enc_file = Path(meta.file_path)
    assert enc_file.exists()
    on_disk_bytes = enc_file.read_bytes()
    assert raw_content not in on_disk_bytes  # Strongly encrypted

    # 3. Retrieve and decrypt
    decrypted_bytes, read_meta = vault.get_document_bytes(user_id, meta.doc_id)
    assert decrypted_bytes == raw_content
    assert read_meta.doc_type == "Income Certificate"

    # 4. List and delete
    docs = vault.list_documents(user_id)
    assert len(docs) == 1
    assert docs[0].doc_id == meta.doc_id

    deleted = vault.delete_document(user_id, meta.doc_id)
    assert deleted is True
    assert len(vault.list_documents(user_id)) == 0
    assert not enc_file.exists()


def test_document_extractor_vision_mock():
    """Verify DocumentExtractor parses multimodal image bytes via LLM."""
    client = LLMClient(google_key="mock", gemini_model="mock")
    extractor = DocumentExtractor(llm_client=client)

    mock_extraction = DocumentExtraction(
        doc_type="Aadhaar Card",
        holder_name="Ramesh Kumar",
        date_of_birth="1985-06-12",
        id_last4="8765",
        per_field_confidence=[
            FieldConfidence(field_name="holder_name", confidence=0.97),
            FieldConfidence(field_name="id_last4", confidence=0.99),
        ],
    )

    with patch.object(client, "generate_vision_structured", return_value=(mock_extraction, LLMResult(ok=True, text="{}"))):
        result = extractor.extract_from_image(
            image_bytes=b"fake-image-bytes",
            mime_type="image/jpeg",
            filename="aadhaar_front.jpg",
        )
        assert result.doc_type == "Aadhaar Card"
        assert result.holder_name == "Ramesh Kumar"
        assert result.id_last4 == "8765"


def test_link_document_to_schemes_mock():
    """Verify LLM links extracted document to schemes based on documents_required."""
    client = LLMClient(google_key="mock", gemini_model="mock")
    extractor = DocumentExtractor(llm_client=client)

    extraction = DocumentExtraction(doc_type="Income Certificate", holder_name="Sita Devi")
    schemes = [
        Scheme(
            id="s1",
            name="National Scholarship",
            ministry="Education",
            description="",
            benefits="",
            official_url="",
            documents_required=["Income Certificate", "Marksheet"],
        ),
        Scheme(
            id="s2",
            name="PM Kisan",
            ministry="Agriculture",
            description="",
            benefits="",
            official_url="",
            documents_required=["Land Record", "Aadhaar Card"],
        ),
    ]

    mock_link_res = LinkedSchemesResult(matched_scheme_ids=["s1"], matching_reason="Income Certificate required for s1")

    with patch.object(client, "generate_structured", return_value=(mock_link_res, LLMResult(ok=True, text="{}"))):
        matched_ids = extractor.link_document_to_schemes(extraction, schemes)
        assert matched_ids == ["s1"]


def test_cross_document_and_profile_consistency_audit():
    """Verify LLM detects name discrepancies and income limit contradictions with evidence."""
    client = LLMClient(google_key="mock", gemini_model="mock")
    extractor = DocumentExtractor(llm_client=client)

    docs = [
        StoredDocumentMetadata(
            doc_id="d1",
            user_id="u1",
            filename="aadhaar.jpg",
            doc_type="Aadhaar Card",
            holder_name="Ananya Verma",
            created_at="2026-01-01",
            file_path="/dummy/d1.enc",
        ),
        StoredDocumentMetadata(
            doc_id="d2",
            user_id="u1",
            filename="income_cert.pdf",
            doc_type="Income Certificate",
            holder_name="Ananya V",
            income_amount=350000,
            created_at="2026-01-01",
            file_path="/dummy/d2.enc",
        ),
    ]

    profile = CitizenProfile(
        annual_income=Fact(value=180000, confidence=1.0),
    )

    mock_report = DocumentConsistencyReport(
        issues=[
            ConsistencyIssue(
                id="issue_name_1",
                severity="medium",
                message="Name on Aadhaar ('Ananya Verma') differs slightly from Income Certificate ('Ananya V').",
                documents=["aadhaar.jpg", "income_cert.pdf"],
                field_name="holder_name",
                evidence="Aadhaar: 'Ananya Verma' vs Income Certificate: 'Ananya V'",
            ),
            ConsistencyIssue(
                id="issue_inc_2",
                severity="high",
                message="Income on certificate (₹3,50,000) exceeds stated profile income (₹1,80,000) and NSP ceiling (₹2,50,000).",
                documents=["income_cert.pdf"],
                field_name="annual_income",
                evidence="Certificate stated income: 350000; Self-reported: 180000",
            ),
        ],
        is_consistent=False,
    )

    with patch.object(client, "generate_structured", return_value=(mock_report, LLMResult(ok=True, text="{}"))):
        report = extractor.audit_consistency(documents=docs, profile=profile)
        assert report.is_consistent is False
        assert len(report.issues) == 2
        assert report.issues[0].field_name == "holder_name"
        assert report.issues[1].severity == "high"
