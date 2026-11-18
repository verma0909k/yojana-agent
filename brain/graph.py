"""LangGraph orchestration loop for YojanaAgent."""

from langgraph.graph import StateGraph, END
from brain.asker import GapAsker
from brain.critic import Critic
from brain.planner import Planner
from brain.trace import TraceLogger
from knowledge.matcher import SchemeMatcher
from knowledge.verifier import Verifier
from shared.schemas import AgentState, EligibilityStatus, TraceStep

# Initialize modules
planner = Planner()
matcher = SchemeMatcher()
asker = GapAsker()
verifier = Verifier()
critic = Critic()


def planner_node(state: AgentState) -> dict:
    """Decides which node executes next."""
    step = state.step_count + 1
    next_node = planner.decide_next_step(state)

    trace = TraceStep(
        agent_name="Planner",
        action=f"Planned step {step} -> Route to: {next_node.upper()}",
        details={"step": step, "next_node": next_node}
    )
    return {
        "step_count": step,
        "next_node": next_node,
        "trace_steps": state.trace_steps + [trace]
    }


def matcher_node(state: AgentState) -> dict:
    """Executes deterministic rule matching over candidate schemes."""
    results = matcher.match(profile=state.profile, query=state.user_query)

    eligible_count = sum(1 for r in results if r.status == EligibilityStatus.ELIGIBLE)
    almost_count = sum(1 for r in results if r.status == EligibilityStatus.ALMOST)

    trace = TraceStep(
        agent_name="Matcher",
        action="Ran deterministic Python rule engine",
        details={
            "total_evaluated": len(results),
            "eligible": eligible_count,
            "almost": almost_count
        }
    )
    return {
        "match_results": results,
        "trace_steps": state.trace_steps + [trace]
    }


def asker_node(state: AgentState) -> dict:
    """Finds highest-impact information gap and generates question."""
    gap_field = asker.find_highest_impact_gap(state.match_results)
    if gap_field:
        question = asker.generate_question(gap_field, language=state.language)
        trace = TraceStep(
            agent_name="Gap-Asker",
            action=f"Identified high-impact gap: {gap_field}",
            details={"gap_field": gap_field, "question": question}
        )
        return {
            "pending_questions": state.pending_questions + [question],
            "trace_steps": state.trace_steps + [trace]
        }
    return {}


def verifier_node(state: AgentState) -> dict:
    """Verifies official portals and document consistency."""
    verified = []
    eligible_results = [r for r in state.match_results if r.status == EligibilityStatus.ELIGIBLE]

    for r in eligible_results[:3]:  # Verify top eligible portals
        status = verifier.check_portal(r.official_url)
        verified.append(f"{r.scheme_name}: {status['message']}")

    inconsistencies = verifier.verify_document_consistency(state.profile)

    trace = TraceStep(
        agent_name="Verifier",
        action="Verified official portals and profile consistency",
        details={"portals_checked": len(verified), "inconsistencies": inconsistencies}
    )
    return {
        "verified_schemes": verified,
        "trace_steps": state.trace_steps + [trace]
    }


def critic_node(state: AgentState) -> dict:
    """Performs safety and hallucination audit on generated recommendations."""
    audit_report = critic.audit(state.match_results)

    trace = TraceStep(
        agent_name="Critic",
        action="Audited results for groundedness and source validation",
        details={"valid": audit_report["is_valid"], "flags_count": len(audit_report["flags"])}
    )
    return {
        "critic_notes": audit_report["flags"] or ["All claims verified and grounded"],
        "trace_steps": state.trace_steps + [trace]
    }


def finalize_node(state: AgentState) -> dict:
    """Formats final response in user language with reasons and official links."""
    eligible = [m for m in state.match_results if m.status == EligibilityStatus.ELIGIBLE]
    almost = [m for m in state.match_results if m.status == EligibilityStatus.ALMOST]

    response_lines = ["### Official Scheme Matching Results\n"]

    if eligible:
        response_lines.append(f"#### Eligible Schemes ({len(eligible)})")
        for m in eligible:
            response_lines.append(f"- **{m.scheme_name}**")
            response_lines.append(f"  - **Benefit**: {m.benefit_summary}")
            response_lines.append(f"  - **Reason**: {', '.join(m.satisfied_reasons)}")
            response_lines.append(f"  - **Official Portal**: [{m.official_url}]({m.official_url})")
            if m.documents_required:
                response_lines.append(f"  - **Required Documents**: {', '.join(m.documents_required)}")
        response_lines.append("")

    if almost:
        response_lines.append(f"#### Almost Eligible ({len(almost)})")
        for m in almost[:5]:
            response_lines.append(f"- **{m.scheme_name}**: Missing info for {', '.join(m.missing_fields)}")
            response_lines.append(f"  - **Official Link**: [{m.official_url}]({m.official_url})")

    trace = TraceStep(
        agent_name="Orchestrator",
        action="Generated structured final response",
        details={"eligible_count": len(eligible), "almost_count": len(almost)}
    )
    return {
        "final_response": "\n".join(response_lines),
        "is_complete": True,
        "trace_steps": state.trace_steps + [trace]
    }


def route_decision(state: AgentState) -> str:
    """Routes based on planner's decided next node."""
    next_node = state.next_node
    if next_node in ["matcher", "asker", "verifier", "critic", "finalize"]:
        return next_node
    return "finalize"


def build_graph():
    """Builds and compiles the LangGraph StateGraph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("matcher", matcher_node)
    workflow.add_node("asker", asker_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("finalize", finalize_node)

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges(
        "planner",
        route_decision,
        {
            "matcher": "matcher",
            "asker": "asker",
            "verifier": "verifier",
            "critic": "critic",
            "finalize": "finalize",
        }
    )

    workflow.add_edge("matcher", "planner")
    workflow.add_edge("asker", "planner")
    workflow.add_edge("verifier", "planner")
    workflow.add_edge("critic", "planner")
    workflow.add_edge("finalize", END)

    return workflow.compile()
