"""Unit tests for Phase 3: Tool Registry, Dynamic Tool Execution, and Observation Feedback Loop."""

import pytest
from brain.graph import build_graph
from brain.tool_registry import ToolRegistry
from shared.schemas import (
    AgentActionType,
    AgentState,
    CitizenProfile,
    Fact,
    Gender,
    Occupation,
    PlanDecision,
    ToolExecutionResult,
)


def test_tool_registry_registration_and_schemas():
    """Verify all 15 required tools are registered with valid Pydantic schemas and descriptions."""
    registry = ToolRegistry()
    assert len(registry.tools) == 15

    expected_tools = [
        "extract_citizen_profile",
        "search_schemes",
        "get_scheme_details",
        "retrieve_scheme_evidence",
        "identify_information_gaps",
        "ask_citizen_question",
        "verify_official_source",
        "compare_eligibility",
        "check_required_documents",
        "prepare_application_checklist",
        "generate_application_document",
        "create_application_task",
        "update_application_status",
        "save_agent_memory",
        "retrieve_agent_memory",
    ]
    for tool_name in expected_tools:
        assert tool_name in registry.tools
        t = registry.get_tool(tool_name)
        assert t is not None
        assert t.description != ""
        assert t.input_schema is not None

    tool_list = registry.list_tools()
    assert len(tool_list) == 15
    for item in tool_list:
        assert "name" in item
        assert "description" in item
        assert "schema" in item


def test_tool_execution_search_and_evidence():
    """Verify search_schemes and retrieve_scheme_evidence return real data and handle invalid inputs gracefully."""
    registry = ToolRegistry()

    # 1. Real search execution
    res = registry.execute_tool("search_schemes", {"query": "farmer irrigation kisan", "top_k": 3})
    assert isinstance(res, ToolExecutionResult)
    assert res.success is True
    assert isinstance(res.data, list)
    assert len(res.data) > 0
    assert any("pm-kisan" in s["scheme_id"] or "pm-kusum" in s["scheme_id"] for s in res.data)

    # 2. Scheme details execution
    detail_res = registry.execute_tool("get_scheme_details", {"scheme_id": "pm-kisan"})
    assert detail_res.success is True
    assert detail_res.data["id"] == "pm-kisan"
    assert "Ministry of Agriculture" in detail_res.data["ministry"]

    # 3. Invalid scheme ID produces typed error without raising
    bad_res = registry.execute_tool("get_scheme_details", {"scheme_id": "non-existent-scheme-999"})
    assert bad_res.success is False
    assert "not found" in bad_res.error

    # 4. Evidence retrieval
    ev_res = registry.execute_tool("retrieve_scheme_evidence", {"scheme_id": "pm-kisan"})
    assert ev_res.success is True
    assert "https://pmkisan.gov.in" in ev_res.data["official_url"]


def test_tool_execution_application_actions(tmp_path):
    """Verify document checks, checklist preparation, and pre-filled PDF generation."""
    registry = ToolRegistry()

    # 1. Document checklist check
    check_res = registry.execute_tool(
        "check_required_documents",
        {
            "scheme_id": "pm-kisan",
            "available_documents": ["Aadhaar Card"]
        }
    )
    assert check_res.success is True
    assert "Aadhaar Card" in check_res.data["ready_documents"][0]
    assert len(check_res.data["missing_documents"]) >= 1
    assert check_res.data["is_complete"] is False

    # 2. Application checklist preparation
    cl_res = registry.execute_tool("prepare_application_checklist", {"scheme_id": "pm-kisan"})
    assert cl_res.success is True
    assert len(cl_res.data["documents_checklist"]) >= 1

    # 3. Real PDF generation tool
    profile = CitizenProfile(
        age=Fact(value=45, confidence=1.0),
        gender=Fact(value=Gender.MALE, confidence=1.0),
        occupation=Fact(value=Occupation.FARMER, confidence=1.0),
    )
    pdf_res = registry.execute_tool(
        "generate_application_document",
        {
            "scheme_id": "pm-kisan",
            "profile_data": profile.model_dump()
        }
    )
    assert pdf_res.success is True
    assert "pdf_path" in pdf_res.data
    import os
    assert os.path.exists(pdf_res.data["pdf_path"])

    # Clean up generated test PDF
    import pathlib
    pathlib.Path(pdf_res.data["pdf_path"]).unlink(missing_ok=True)


def test_dynamic_tool_execution_in_langgraph_loop():
    """Verify LangGraph tool_executor node executes tool dynamically and feeds observation back to state."""
    graph = build_graph()

    # Create state with an explicit dynamic plan to search schemes
    state = AgentState(
        user_query="Need loan for self employment or business",
        profile=CitizenProfile(
            age=Fact(value=30, confidence=1.0),
            occupation=Fact(value=Occupation.SELF_EMPLOYED, confidence=1.0),
        ),
        plan_decision=PlanDecision(
            citizen_goal="Find self employment loan",
            current_understanding="Applicant is self-employed seeking business credit",
            information_gaps=[],
            proposed_action=AgentActionType.SEARCH_SCHEMES,
            selected_tool="search_schemes",
            tool_args={"query": "business loan mudra pmegp", "top_k": 3},
            expected_outcome="Credit schemes retrieved",
            reason="Search credit schemes for enterprise",
            is_terminal=False,
        ),
        next_node="tool_executor",
    )

    # Invoke graph starting from tool_executor
    result = graph.invoke(state)
    assert result["is_complete"] is True
    assert "last_tool_result" in result["execution_context"]
    assert result["execution_context"]["last_tool_result"]["success"] is True

    # Assert ToolExecutor trace was recorded
    tool_traces = [t for t in result["trace_steps"] if t.agent_name == "ToolExecutor"]
    assert len(tool_traces) >= 1
    assert "search_schemes" in tool_traces[0].action
