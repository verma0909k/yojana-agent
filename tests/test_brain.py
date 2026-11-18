"""Tests for brain layer: LangGraph loop, Planner, Gap-Asker, Critic."""

from yojanaagent.brain.asker import GapAsker
from yojanaagent.brain.critic import Critic
from yojanaagent.brain.graph import build_graph
from yojanaagent.experience.personas.demo_profiles import get_farmer_persona
from yojanaagent.knowledge.schemes import load_all_schemes
from yojanaagent.shared.schemas import AgentState, EligibilityStatus, MatchResult


def test_gap_asker():
    asker = GapAsker()
    dummy_matches = [
        MatchResult(
            scheme_id="s1",
            scheme_name="Scheme 1",
            status=EligibilityStatus.ALMOST,
            missing_fields=["is_bpl", "annual_income"]
        ),
        MatchResult(
            scheme_id="s2",
            scheme_name="Scheme 2",
            status=EligibilityStatus.ALMOST,
            missing_fields=["is_bpl"]
        )
    ]
    top_gap = asker.find_highest_impact_gap(dummy_matches)
    assert top_gap == "is_bpl"

    question_en = asker.generate_question(top_gap, language="en")
    assert "BPL" in question_en


def test_critic_audit():
    critic = Critic()
    valid_matches = [
        MatchResult(
            scheme_id="pm-kisan",
            scheme_name="PM Kisan",
            status=EligibilityStatus.ELIGIBLE,
            satisfied_reasons=["Farmer occupation verified"],
            official_url="https://pmkisan.gov.in"
        )
    ]
    report = critic.audit(valid_matches)
    assert report["is_valid"] is True


def test_langgraph_execution():
    graph = build_graph()
    farmer = get_farmer_persona()

    state = AgentState(profile=farmer, user_query="agriculture schemes", language="en")
    result = graph.invoke(state)

    assert result["is_complete"] is True
    assert len(result["trace_steps"]) > 0
    assert len(result["match_results"]) > 0
