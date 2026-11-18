"""Unit tests for Phase 1: LLM Brain, Structured Pydantic Planning, and Goal-Driven Reasoning."""

import json
from unittest.mock import MagicMock, patch
import pytest
from brain.graph import build_graph
from brain.llm_client import LLMClient, LLMResult, LLMUnavailableError
from brain.planner import Planner
from shared.schemas import (
    AgentActionType,
    AgentState,
    CitizenProfile,
    EligibilityConfidence,
    EvidenceGrounding,
    Fact,
    Gender,
    Occupation,
    PlanDecision,
)


def test_pydantic_planning_schemas():
    """Verify that PlanDecision, EligibilityConfidence, and EvidenceGrounding serialize/validate cleanly."""
    decision = PlanDecision(
        citizen_goal="Find technical college scholarship for women",
        current_understanding="Applicant is a 20yo female student in Bihar studying engineering",
        information_gaps=["annual_income"],
        proposed_action=AgentActionType.SEARCH_SCHEMES,
        selected_tool="search_schemes",
        tool_args={"category": "scholarship", "target_group": "women"},
        expected_outcome="Targeted list of merit scholarships",
        reason="Initial retrieval based on student criteria",
        is_terminal=False,
    )
    assert decision.proposed_action == AgentActionType.SEARCH_SCHEMES
    assert decision.selected_tool == "search_schemes"
    assert "annual_income" in decision.information_gaps

    dumped = decision.model_dump_json()
    reloaded = PlanDecision.model_validate_json(dumped)
    assert reloaded.citizen_goal == decision.citizen_goal
    assert reloaded.proposed_action == AgentActionType.SEARCH_SCHEMES

    # Evidence grounding schema
    evidence = EvidenceGrounding(
        claim="Annual income limit is Rs 8 Lakh",
        source_url="https://www.aicte-india.org/pragati",
        source_quote="Maximum annual family income should not exceed 8,00,000",
        confidence=0.95,
        status="verified",
    )
    assert evidence.confidence == 0.95
    assert evidence.status == "verified"


def test_llm_client_generate_structured():
    """Verify that generate_structured parses JSON models cleanly, including handling markdown code fences."""
    client = LLMClient(google_key="mock-key", gemini_model="gemini-2.0-flash")
    
    mock_decision_data = {
        "citizen_goal": "Apply for Mudra loan for micro-business",
        "current_understanding": "Applicant wants to start a textile shop",
        "information_gaps": ["annual_income", "existing_loans"],
        "proposed_action": "search_schemes",
        "selected_tool": "search_schemes",
        "tool_args": {"keywords": ["mudra", "business loan"]},
        "expected_outcome": "Mudra and PMEGP details retrieved",
        "reason": "Citizen needs credit for enterprise setup",
        "requires_replanning": False,
        "requires_approval": False,
        "is_terminal": False,
    }

    # Case 1: Raw JSON output
    with patch.object(client, "generate", return_value=LLMResult(ok=True, text=json.dumps(mock_decision_data), provider="gemini")):
        instance, res = client.generate_structured("Plan for Mudra", PlanDecision)
        assert res.ok is True
        assert isinstance(instance, PlanDecision)
        assert instance.citizen_goal == "Apply for Mudra loan for micro-business"
        assert instance.selected_tool == "search_schemes"

    # Case 2: Output enclosed in markdown ```json ... ``` code fence
    markdown_wrapped = f"```json\n{json.dumps(mock_decision_data)}\n```"
    with patch.object(client, "generate", return_value=LLMResult(ok=True, text=markdown_wrapped, provider="gemini")):
        instance, res = client.generate_structured("Plan for Mudra", PlanDecision)
        assert res.ok is True
        assert isinstance(instance, PlanDecision)
        assert instance.proposed_action == AgentActionType.SEARCH_SCHEMES

    # Case 3: Provider unconfigured
    unconfigured_client = LLMClient(google_key="", anthropic_key="")
    with pytest.raises(LLMUnavailableError, match="LLM provider not configured"):
        unconfigured_client.generate_structured("Plan", PlanDecision)

    with pytest.raises(LLMUnavailableError):
        unconfigured_client.generate_structured("Plan", PlanDecision, raise_on_error=True)


def test_goal_driven_planning_scenarios():
    """Verify that different citizen goals produce distinctly different plans and tools."""
    planner = Planner()

    # Scenario A: Student scholarship goal
    student_state = AgentState(
        user_query="I am a girl student in engineering college, need scholarship assistance",
        profile=CitizenProfile(
            age=Fact(value=20, confidence=1.0),
            gender=Fact(value=Gender.FEMALE, confidence=1.0),
            occupation=Fact(value=Occupation.STUDENT, confidence=1.0),
        ),
    )
    plan_a = planner.plan(student_state)
    assert plan_a.citizen_goal == student_state.user_query
    assert plan_a.selected_tool == "search_schemes"

    # Scenario B: Farmer seeking solar pump subsidy
    farmer_state = AgentState(
        user_query="Mujhe khet me solar water pump lagwana hai, kya subsidy milegi?",
        profile=CitizenProfile(
            age=Fact(value=48, confidence=1.0),
            gender=Fact(value=Gender.MALE, confidence=1.0),
            occupation=Fact(value=Occupation.FARMER, confidence=1.0),
        ),
    )
    plan_b = planner.plan(farmer_state)
    assert plan_b.citizen_goal == farmer_state.user_query

    # Both scenarios have unique, goal-specific context
    assert plan_a.citizen_goal != plan_b.citizen_goal


def test_graph_executes_with_structured_planner():
    """Verify that LangGraph loop invokes structured planner and populates current_goal and plan_decision."""
    graph = build_graph()
    initial_state = AgentState(
        user_query="Need agricultural loan or equipment subsidy",
        profile=CitizenProfile(
            age=Fact(value=45, confidence=1.0),
            occupation=Fact(value=Occupation.FARMER, confidence=1.0),
        ),
    )

    with patch("knowledge.verifier.Verifier.check_portals_concurrently", return_value={}):
        final_state = graph.invoke(initial_state)

    assert final_state["current_goal"] != ""
    assert final_state["plan_decision"] is not None
    assert isinstance(final_state["plan_decision"], PlanDecision)
    assert len(final_state["plan_history"]) >= 1

    # Verify trace steps logged planning decisions with structured details
    planner_traces = [t for t in final_state["trace_steps"] if t.agent_name == "Planner"]
    assert len(planner_traces) >= 1
    assert "selected_tool" in planner_traces[0].details
