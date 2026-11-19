"""Unit tests for Phase 5: Grounded LLM-Driven Matcher, Evidence Quotes,
Reviewer Audit, Empathetic Rejection Explanations, Next-Best Recommendations,
and Profile vs Document Conflict Resolution.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from brain.asker import GapAsker
from brain.llm_client import LLMClient, LLMResult, LLMUnavailableError
from brain.tool_registry import ToolRegistry
from knowledge.llm_matcher import LLMMatcher
from knowledge.matcher import SchemeMatcher
from knowledge.schemes.data import load_all_schemes
from shared.schemas import (
    CitizenProfile,
    DocumentExtraction,
    EligibilityStatus,
    Fact,
    GroundedEligibilityVerdict,
    MatchResult,
    NextBestSchemeRecommendation,
    ProfileConflictItem,
    RejectionExplanation,
    ReviewerAuditResult,
    Scheme,
    Source,
)


@pytest.fixture
def mock_llm_client():
    client = MagicMock(spec=LLMClient)
    client.is_available.return_value = True
    return client


@pytest.fixture
def sample_scheme():
    all_schemes = load_all_schemes()
    # Find PM-Kisan
    pm_kisan = next((s for s in all_schemes if s.id == "pm-kisan"), all_schemes[0])
    return pm_kisan


def test_grounded_scheme_evaluation(mock_llm_client, sample_scheme):
    """Test grounded eligibility assessment with mandatory source quotes."""
    verdict_mock = GroundedEligibilityVerdict(
        scheme_id=sample_scheme.id,
        scheme_name=sample_scheme.name,
        status="ELIGIBLE",
        confidence=0.92,
        evidence_quotes=["Small and marginal landholder farmer families with cultivable land are eligible."],
        satisfied_reasons=["Applicant owns 1.5 acres of agricultural land."],
        missing_fields=[],
        disqualifying_reasons=[],
        date_calculation_reasoning="Applicant age is 35 as of current date.",
        explanation="You meet all requirements for PM-Kisan financial support.",
        benefit_summary="₹6,000 per year in three equal installments.",
        documents_required=["Aadhaar", "Land Ownership Record"],
    )
    audit_mock = ReviewerAuditResult(
        agrees=True,
        audit_confidence=0.95,
        reason="Determination directly grounded in PM-Kisan guidelines.",
    )

    mock_llm_client.generate_structured.side_effect = [
        (verdict_mock, LLMResult(ok=True, text="")),
        (audit_mock, LLMResult(ok=True, text="")),
    ]

    matcher = LLMMatcher(llm_client=mock_llm_client)
    profile = CitizenProfile()
    profile.occupation = Fact(value="farmer", known=True)
    profile.land_holding_acres = Fact(value=1.5, known=True)

    result = matcher.evaluate_scheme_grounded(profile, sample_scheme)

    assert result.status == "ELIGIBLE"
    assert result.confidence >= 0.7
    assert len(result.evidence_quotes) > 0
    assert result.needs_review is False
    assert "PM-Kisan" in result.explanation or "financial support" in result.explanation


def test_reviewer_disagreement_forces_needs_review(mock_llm_client, sample_scheme):
    """Test that Reviewer audit disagreement forces status to NEEDS_REVIEW."""
    verdict_mock = GroundedEligibilityVerdict(
        scheme_id=sample_scheme.id,
        scheme_name=sample_scheme.name,
        status="ELIGIBLE",
        confidence=0.88,
        evidence_quotes=["Land holding requirement up to 2 hectares."],
        satisfied_reasons=[],
        missing_fields=[],
        disqualifying_reasons=[],
    )
    # Reviewer disagrees: detects applicant is an institutional landholder
    audit_disagree = ReviewerAuditResult(
        agrees=False,
        audit_confidence=0.90,
        reason="Applicant profile indicates non-cultivable institutional land.",
    )

    mock_llm_client.generate_structured.side_effect = [
        (verdict_mock, LLMResult(ok=True, text="")),
        (audit_disagree, LLMResult(ok=True, text="")),
    ]

    matcher = LLMMatcher(llm_client=mock_llm_client)
    profile = CitizenProfile()

    result = matcher.evaluate_scheme_grounded(profile, sample_scheme)

    assert result.status == "NEEDS_REVIEW"
    assert result.needs_review is True
    assert "Auditor disagreement" in result.audit_notes


def test_explain_rejection_and_next_best(mock_llm_client, sample_scheme):
    """Test compassionate explanation and next-best alternative recommendations."""
    verdict = GroundedEligibilityVerdict(
        scheme_id=sample_scheme.id,
        scheme_name=sample_scheme.name,
        status="NOT_ELIGIBLE",
        confidence=0.95,
        evidence_quotes=["Applicants who pay income tax are excluded from the scheme."],
        disqualifying_reasons=["Family pays income tax"],
        explanation="Ineligible due to income tax exclusion criteria.",
    )

    rejection_mock = RejectionExplanation(
        scheme_id=sample_scheme.id,
        scheme_name=sample_scheme.name,
        plain_language_reason="PM-Kisan is reserved for farmers not subject to income tax. Your tax filing status makes this program unavailable.",
        blocking_criteria=["Income tax assessment exclusion"],
        evidence_quote="Applicants who pay income tax are excluded from the scheme.",
        suggested_next_steps=["Check Kisan Credit Card or agricultural infrastructure loan subsidies instead."],
        alternative_schemes=["pmmy-mudra", "kisan-credit-card"],
    )
    mock_llm_client.generate_structured.return_value = (rejection_mock, LLMResult(ok=True, text=""))

    matcher = LLMMatcher(llm_client=mock_llm_client)
    explanation = matcher.explain_rejection(verdict, language="en")

    assert explanation.scheme_id == sample_scheme.id
    assert "tax" in explanation.plain_language_reason.lower()
    assert len(explanation.suggested_next_steps) > 0

    # Next-best recommendations
    profile = CitizenProfile()
    recs = matcher.recommend_next_best(profile, ineligible_scheme_id=sample_scheme.id, top_k=2)
    assert len(recs) <= 2
    for r in recs:
        assert r.scheme_id != sample_scheme.id


def test_spot_profile_and_document_conflicts(mock_llm_client):
    """Test GapAsker identifying discrepancies between stated profile facts and vault documents."""
    profile = CitizenProfile()
    profile.annual_income = Fact(value=150000, known=True, source=Source.USER_TEXT)

    doc_extraction = DocumentExtraction(
        doc_type="Income Certificate",
        holder_name="Ramesh Kumar",
        income_amount=280000,
        issue_date="2024-03-01",
    )

    asker = GapAsker(llm_client=mock_llm_client)
    conflicts = asker.spot_profile_conflicts(profile, [doc_extraction])

    assert len(conflicts) > 0
    income_conflict = conflicts[0]
    assert income_conflict.field_name == "annual_income"
    assert income_conflict.conflict_severity == "HIGH"
    assert "₹150,000" in income_conflict.stated_value
    assert "₹280,000" in income_conflict.document_value
    assert len(income_conflict.clarification_question_en) > 0
    assert len(income_conflict.clarification_question_hi) > 0

    # Test get_next_question prioritizes conflict resolution
    next_q = asker.get_next_question(match_results=[], profile=profile, documents=[doc_extraction])
    assert next_q is not None
    assert next_q["type"] == "CONFLICT_RESOLUTION"
    assert next_q["field_name"] == "annual_income"


def test_scheme_matcher_decision_modes(mock_llm_client, sample_scheme):
    """Test DECISION_MODE=rules fallback vs DECISION_MODE=llm without silent fallbacks."""
    profile = CitizenProfile()
    profile.occupation = Fact(value="farmer", known=True)
    profile.land_holding_acres = Fact(value=1.5, known=True)

    # 1. Deterministic rules mode
    matcher_rules = SchemeMatcher(decision_mode="rules")
    rule_results = matcher_rules.match(profile, query="farmer")
    assert isinstance(rule_results, list)
    assert len(rule_results) > 0

    # 2. LLM mode when LLM is unavailable must raise LLMUnavailableError (No silent fallback!)
    offline_llm = LLMClient(google_key="", anthropic_key="")
    matcher_offline = SchemeMatcher(
        llm_matcher=LLMMatcher(llm_client=offline_llm),
        decision_mode="llm",
    )
    with pytest.raises(LLMUnavailableError):
        matcher_offline.match(profile, query="farmer")


def test_tool_registry_phase5_tools():
    """Verify tool registry includes vault inspection, notification drafting, and rejection explanations."""
    registry = ToolRegistry()
    tools = {t["name"]: t for t in registry.list_tools()}

    assert "get_vault_documents" in tools
    assert "draft_notification" in tools
    assert "explain_rejection" in tools
    assert "recommend_next_best" in tools

    # Execute get_vault_documents for a clean user
    res = registry.execute_tool("get_vault_documents", {"user_id": "test_phase5_user"})
    assert res.success is True
    assert isinstance(res.data, list)
