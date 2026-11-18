"""Tests for Phase 5: Evidentiary Grounding, Official Portal Verifier, and Critic Self-Correction."""

from unittest.mock import MagicMock, patch

from brain.critic import Critic, DISCLAIMER_TEXT
from brain.graph import critic_node
from knowledge.verifier import Verifier
from shared.schemas import (
    AgentActionType,
    AgentState,
    EligibilityConfidence,
    EligibilityStatus,
    EvidenceGrounding,
    MatchResult,
    PlanDecision,
)


def test_verifier_fetch_evidence_handling():
    """Verify Verifier fetches or safely handles portal evidence offline and with errors."""
    v = Verifier()

    # Invalid URL
    res_invalid = v.fetch_official_evidence("")
    assert res_invalid["success"] is False
    assert res_invalid["error"] == "Invalid URL"

    # Mocked HTML response
    fake_html = "<html><head><title>Portal</title><script>var x=1;</script></head><body><h1>Scheme Guidelines</h1><p>Eligibility requires 18 years.</p></body></html>"
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = fake_html
        mock_get.return_value = mock_resp

        res = v.fetch_official_evidence("https://scholarships.gov.in")
        assert res["success"] is True
        assert "Eligibility requires 18 years." in res["text_excerpt"]
        assert "var x=1" not in res["text_excerpt"]  # script stripped


def test_critic_grounding_audit_and_confidence():
    """Verify Critic computes granular confidence levels and rejects ungrounded claims."""
    critic = Critic()

    valid_eligible = MatchResult(
        scheme_id="pm-kisan",
        scheme_name="PM Kisan",
        status=EligibilityStatus.ELIGIBLE,
        satisfied_reasons=["Farmer occupation confirmed"],
        official_url="https://pmkisan.gov.in"
    )
    ungrounded_eligible = MatchResult(
        scheme_id="fake-scheme",
        scheme_name="Fake Scheme",
        status=EligibilityStatus.ELIGIBLE,
        satisfied_reasons=[],  # Empty reasons -> ungrounded
        official_url="https://fake.gov.in"
    )
    no_url_scheme = MatchResult(
        scheme_id="bad-scheme",
        scheme_name="Bad Scheme",
        status=EligibilityStatus.ALMOST,
        missing_fields=["age"],
        official_url=""  # Missing URL
    )

    results = [valid_eligible, ungrounded_eligible, no_url_scheme]
    audit = critic.audit(results)

    assert audit["is_valid"] is False
    assert audit["pruned_count"] == 2
    assert len(audit["approved_results"]) == 1
    assert audit["approved_results"][0].scheme_id == "pm-kisan"
    assert audit["confidence_assessments"]["pm-kisan"] == EligibilityConfidence.LIKELY_ELIGIBLE
    assert DISCLAIMER_TEXT in audit["disclaimer"]


def test_critic_triggers_replanning_on_hallucinations():
    """Verify Critic flags requires_replanning when candidate recommendations fail grounding."""
    critic = Critic()

    hallucinated_scheme = MatchResult(
        scheme_id="phantom-scholarship",
        scheme_name="Phantom Scholarship",
        status=EligibilityStatus.ELIGIBLE,
        satisfied_reasons=[],
        official_url="ftp://invalid-url"
    )

    audit = critic.audit([hallucinated_scheme])
    assert audit["requires_replanning"] is True
    assert len(audit["replanning_notes"]) >= 1
    assert "pruned for lack of grounding" in audit["replanning_notes"][0]


def test_critic_node_integration_in_graph():
    """Verify critic_node updates state and flags requires_replanning on plan decision."""
    state = AgentState(
        user_query="Need startup grant",
        candidate_schemes=["phantom-grant"],
        match_results=[
            MatchResult(
                scheme_id="phantom-grant",
                scheme_name="Phantom Grant",
                status=EligibilityStatus.ELIGIBLE,
                satisfied_reasons=[],
                official_url=""
            )
        ],
        plan_decision=PlanDecision(
            citizen_goal="Find startup grants",
            current_understanding="Searching grants",
            information_gaps=[],
            proposed_action=AgentActionType.COMPARE_ELIGIBILITY,
            selected_tool="compare_eligibility",
            tool_args={},
            expected_outcome="Grants evaluated",
            reason="Check grant eligibility",
            requires_replanning=False,
            is_terminal=False,
        )
    )

    updates = critic_node(state)
    assert len(updates["match_results"]) == 0
    assert updates["plan_decision"].requires_replanning is True
    assert "Critic flagged ungrounded results" in updates["plan_decision"].reason
    assert any(t.agent_name == "Critic" for t in updates["trace_steps"])
