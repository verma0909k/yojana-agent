"""Tests for Phase 4: StateManager, SQLite persistence, and LangGraph interrupt/resume workflow."""

import pytest
from pathlib import Path
import tempfile

from brain.graph import build_graph
from brain.state_manager import StateManager
from shared.schemas import (
    AgentActionType,
    AgentState,
    CitizenProfile,
    EligibilityStatus,
    Fact,
    MatchResult,
    Occupation,
    PlanDecision,
    TraceStep,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    return tmp_path / "test_sessions.db"


def test_state_manager_sqlite_crud(temp_db: Path):
    """Verify SQLite saving, loading, listing, and deletion of full AgentState."""
    sm = StateManager(db_path=temp_db)

    profile = CitizenProfile(
        age=Fact(value=28, confidence=1.0),
        occupation=Fact(value=Occupation.FARMER, confidence=1.0),
    )
    state = AgentState(
        session_id="session_abc_123",
        user_query="Need agricultural subsidies",
        profile=profile,
        candidate_schemes=["pm-kisan"],
        match_results=[
            MatchResult(
                scheme_id="pm-kisan",
                scheme_name="PM Kisan",
                status=EligibilityStatus.ELIGIBLE,
                satisfied_reasons=["Farmer occupation confirmed"],
                official_url="https://pmkisan.gov.in"
            )
        ],
        trace_steps=[
            TraceStep(agent_name="Planner", action="Initial plan", details={"step": 1})
        ]
    )

    # 1. Save
    sm.save_session("session_abc_123", state)

    # 2. Load
    loaded = sm.load_session("session_abc_123")
    assert loaded is not None
    assert loaded.session_id == "session_abc_123"
    assert loaded.user_query == "Need agricultural subsidies"
    assert loaded.profile.age.value == 28
    assert loaded.candidate_schemes == ["pm-kisan"]
    assert len(loaded.match_results) == 1
    assert loaded.match_results[0].scheme_id == "pm-kisan"
    assert len(loaded.trace_steps) == 1

    # 3. List
    sessions = sm.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session_abc_123"

    # 4. Delete
    deleted = sm.delete_session("session_abc_123")
    assert deleted is True
    assert sm.load_session("session_abc_123") is None


def test_pause_and_resume_session(temp_db: Path):
    """Verify pausing a session on missing fact and resuming with natural language response."""
    sm = StateManager(db_path=temp_db)

    state = AgentState(
        session_id="sess_farmer_001",
        user_query="Kisan credit card apply karna hai",
        profile=CitizenProfile(
            occupation=Fact(value=Occupation.FARMER, confidence=1.0)
        ),
        pending_questions=["How many acres of agricultural land do you own?"],
        asked_fields=["land_holding_acres"]
    )

    # Pause
    paused_state = sm.pause_session("sess_farmer_001", state, reason="Awaiting land acreage")
    assert paused_state.is_paused is True
    assert paused_state.pause_reason == "Awaiting land acreage"

    # Verify persisted in DB as paused
    loaded_paused = sm.load_session("sess_farmer_001")
    assert loaded_paused.is_paused is True

    # Citizen answers: "Mere paas 4.5 acre zameen hai"
    resumed = sm.resume_session("sess_farmer_001", citizen_reply="Mere paas 4.5 acre zameen hai")

    assert resumed.is_paused is False
    assert resumed.pause_reason == ""
    assert len(resumed.pending_questions) == 0
    assert resumed.profile.land_holding_acres.known is True
    assert resumed.profile.land_holding_acres.value == 4.5


def test_langgraph_interrupt_on_question(temp_db: Path):
    """Verify LangGraph halts at pause node when pause_on_question=True."""
    graph = build_graph()

    # Create state where plan chooses to ask citizen question and pauses
    state = AgentState(
        session_id="test_pause_graph",
        user_query="Scholarship application",
        profile=CitizenProfile(
            occupation=Fact(value=Occupation.STUDENT, confidence=1.0)
        ),
        plan_decision=PlanDecision(
            citizen_goal="Apply for student scholarship",
            current_understanding="Student looking for scholarship, need age",
            information_gaps=["age"],
            proposed_action=AgentActionType.ASK_CITIZEN_QUESTION,
            selected_tool="ask_citizen_question",
            tool_args={"field_name": "age", "language": "en"},
            expected_outcome="Age question asked",
            reason="Age is missing",
            is_terminal=False,
        ),
        next_node="tool_executor",
        execution_context={"pause_on_question": True}
    )

    result = graph.invoke(state)

    assert result["is_paused"] is True
    assert "Awaiting citizen response on: age" in result["pause_reason"]
    assert len(result["pending_questions"]) == 1
    assert "age" in result["asked_fields"]

    # Assert pause trace recorded
    interrupt_traces = [t for t in result["trace_steps"] if t.agent_name == "GraphInterrupt"]
    assert len(interrupt_traces) >= 1


def test_langgraph_resume_and_complete(temp_db: Path):
    """Verify that after resuming a paused session, LangGraph completes execution."""
    sm = StateManager(db_path=temp_db)

    # 1. Setup paused state in DB
    init_state = AgentState(
        session_id="resume_flow_01",
        user_query="Scholarship for student",
        profile=CitizenProfile(
            occupation=Fact(value=Occupation.STUDENT, confidence=1.0),
            has_aadhaar=Fact(value=True, confidence=1.0),
            has_bank_account=Fact(value=True, confidence=1.0),
        ),
        candidate_schemes=["nsp-national-scholarship-portal"],
        pending_questions=["Could you please share your age?"],
        asked_fields=["age"],
        is_paused=True,
        pause_reason="Awaiting citizen response on: age",
    )
    sm.save_session("resume_flow_01", init_state)

    # 2. Citizen responds with age
    resumed_state = sm.resume_session("resume_flow_01", citizen_reply="I am 20 years old")
    assert resumed_state.profile.age.known is True
    assert resumed_state.profile.age.value == 20
    assert resumed_state.is_paused is False

    # 3. Resume LangGraph execution
    graph = build_graph()
    final_result = graph.invoke(resumed_state)

    assert final_result["is_complete"] is True
    assert len(final_result["match_results"]) > 0
    assert any(m.scheme_id == "nsp-national-scholarship-portal" for m in final_result["match_results"])
