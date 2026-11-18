"""Planner / Orchestrator for YojanaAgent powered by LLM Brain with structured decision making."""

from typing import Any, Optional
from brain.llm_client import LLMClient
from shared.schemas import (
    AgentActionType,
    AgentState,
    EligibilityStatus,
    PlanDecision,
)

PLANNER_SYSTEM_PROMPT = """You are the master reasoning and planning brain of YojanaAgent, an autonomous government welfare assistant for Indian citizens.
Your job is to analyze the citizen's actual goal, known profile facts, and available information to formulate the single best next action.

Guidelines:
1. Understand the citizen's specific goal (e.g. agricultural grant, college scholarship, medical coverage, self-employment loan).
2. Different goals MUST produce different plans and tool selections.
3. Identify genuine information gaps that change eligibility. Do not ask redundant questions.
4. If candidate schemes have not been searched or evaluated, plan a SEARCH_SCHEMES or EXTRACT_PROFILE action.
5. If a high-impact gap prevents confirming eligibility, propose ASK_CITIZEN_QUESTION for only that vital field.
6. If eligible schemes have not been verified against live official sources, propose VERIFY_OFFICIAL_SOURCE.
7. If all necessary steps are done or the step limit is near, propose FINALIZE.
8. Output strictly valid JSON matching the PlanDecision schema."""


class Planner:
    """LLM-powered reasoning planner that generates structured PlanDecision objects."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def build_planning_prompt(self, state: AgentState) -> str:
        """Constructs an exhaustive context prompt for the LLM Brain."""
        known_facts = state.profile.known_fields()
        facts_summary = ", ".join(f"{k}={v}" for k, v in known_facts.items()) if known_facts else "None recorded yet"
        
        matches_summary = ""
        if state.match_results:
            eligible = [m.scheme_name for m in state.match_results if m.status == EligibilityStatus.ELIGIBLE]
            almost = [f"{m.scheme_name} (missing: {', '.join(m.missing_fields)})" for m in state.match_results if m.status == EligibilityStatus.ALMOST]
            matches_summary = f"Eligible: {eligible or 'None'}. Almost Eligible: {almost or 'None'}."
        else:
            matches_summary = "Schemes not yet retrieved or evaluated."

        past_actions = [f"Step {i+1}: {step.agent_name} -> {step.action}" for i, step in enumerate(state.trace_steps[-4:])]
        past_actions_summary = "; ".join(past_actions) if past_actions else "None yet (Initial step)"

        return (
            f"Citizen Query / Request: \"{state.user_query}\"\n"
            f"Language: {state.language}\n"
            f"Current Known Facts: {facts_summary}\n"
            f"Previously Asked Questions / Fields: {state.asked_fields}\n"
            f"Current Matching Status: {matches_summary}\n"
            f"Recent Execution Steps: {past_actions_summary}\n"
            f"Current Step: {state.step_count} of max {state.max_steps}\n\n"
            f"Decide the next best action and tool call for the agent to take."
        )

    def plan(self, state: AgentState) -> PlanDecision:
        """Generates a structured PlanDecision using the LLM Brain."""
        # 1. Hard safety limit on step count
        if state.step_count >= state.max_steps:
            return PlanDecision(
                citizen_goal=state.user_query or "Complete scheme evaluation",
                current_understanding="Execution step limit reached. Concluding evaluation.",
                information_gaps=[],
                proposed_action=AgentActionType.FINALIZE,
                selected_tool="finalize",
                tool_args={},
                expected_outcome="Deliver final verified findings to the citizen.",
                reason="Maximum agent iteration steps reached.",
                is_terminal=True,
            )

        # 2. If LLM provider is available, use structured generation
        if self.llm_client.is_available():
            prompt = self.build_planning_prompt(state)
            decision, res = self.llm_client.generate_structured(
                prompt=prompt,
                schema_class=PlanDecision,
                system_prompt=PLANNER_SYSTEM_PROMPT,
            )
            if decision is not None:
                # Safeguard against duplicate terminal loops
                if len(state.plan_history) >= 1:
                    last_plan = state.plan_history[-1]
                    if (
                        last_plan.proposed_action == decision.proposed_action
                        and last_plan.selected_tool == decision.selected_tool
                        and last_plan.tool_args == decision.tool_args
                        and decision.proposed_action == AgentActionType.ASK_CITIZEN_QUESTION
                    ):
                        decision.proposed_action = AgentActionType.FINALIZE
                        decision.selected_tool = "finalize"
                        decision.is_terminal = True
                        decision.reason = "Duplicate question avoided. Progressing to finalization."
                return decision

        # 3. Explicit heuristic fallback mode (labeled clearly, never pretending to be LLM)
        return self._heuristic_fallback_plan(state)

    def _heuristic_fallback_plan(self, state: AgentState) -> PlanDecision:
        """Deterministically plans the next step when LLM is unavailable or offline."""
        goal = state.user_query or "Discover and evaluate eligible government schemes"
        known = state.profile.known_fields()
        
        # Step A: Semantic search if no candidate schemes and no match results yet
        if not state.candidate_schemes and not state.match_results:
            return PlanDecision(
                citizen_goal=goal,
                current_understanding="Citizen facts recorded. Need to query knowledge base for candidate schemes.",
                information_gaps=[f for f in state.profile.unknown_fields()[:3]],
                proposed_action=AgentActionType.SEARCH_SCHEMES,
                selected_tool="search_schemes",
                tool_args={"query": state.user_query or "government schemes", "top_k": 5},
                expected_outcome="Candidate government schemes evaluated for eligibility.",
                reason="[Fallback Mode: Heuristic Rule] Search relevant schemes from vector store.",
                is_terminal=False,
            )

        # Step B: Compare eligibility if candidates found but match results not yet computed
        if state.candidate_schemes and not state.match_results:
            return PlanDecision(
                citizen_goal=goal,
                current_understanding=f"Retrieved {len(state.candidate_schemes)} candidate schemes. Evaluating eligibility against citizen facts.",
                information_gaps=[],
                proposed_action=AgentActionType.COMPARE_ELIGIBILITY,
                selected_tool="compare_eligibility",
                tool_args={"scheme_ids": state.candidate_schemes, "profile_data": known},
                expected_outcome="Eligibility comparison results generated.",
                reason="[Fallback Mode: Heuristic Rule] Compare citizen facts against candidate scheme criteria.",
                is_terminal=False,
            )

        # Step C: Check for unasked gaps on ALMOST schemes
        almost_matches = [m for m in state.match_results if m.status == EligibilityStatus.ALMOST]
        all_missing = {field for m in almost_matches for field in m.missing_fields}
        unasked_gaps = sorted(list(all_missing - set(state.asked_fields)))

        if almost_matches and unasked_gaps and len(state.pending_questions) < 1:
            gap_field = unasked_gaps[0]
            return PlanDecision(
                citizen_goal=goal,
                current_understanding=f"Found {len(almost_matches)} schemes blocked by missing facts. Top gap: {gap_field}.",
                information_gaps=unasked_gaps,
                proposed_action=AgentActionType.ASK_CITIZEN_QUESTION,
                selected_tool="ask_citizen_question",
                tool_args={"field_name": gap_field, "language": state.language},
                expected_outcome=f"Clarification on {gap_field} from citizen.",
                reason=f"[Fallback Mode: Heuristic Rule] Resolving blocker for {len(almost_matches)} almost-eligible schemes.",
                is_terminal=False,
            )

        # Step D: Portal verification for eligible schemes
        eligible_schemes = [m for m in state.match_results if m.status == EligibilityStatus.ELIGIBLE]
        unverified_urls = [m.official_url for m in eligible_schemes if m.official_url and m.official_url not in state.portal_checks]
        if unverified_urls:
            target_url = unverified_urls[0]
            return PlanDecision(
                citizen_goal=goal,
                current_understanding=f"Identified {len(eligible_schemes)} eligible schemes. Need live portal verification.",
                information_gaps=[],
                proposed_action=AgentActionType.VERIFY_OFFICIAL_SOURCE,
                selected_tool="verify_official_source",
                tool_args={"url": target_url},
                expected_outcome="Official government portals reachability verified.",
                reason="[Fallback Mode: Heuristic Rule] Verify portal integrity before reporting.",
                is_terminal=False,
            )

        # Step E: Finalize
        return PlanDecision(
            citizen_goal=goal,
            current_understanding="All required checks completed successfully.",
            information_gaps=[],
            proposed_action=AgentActionType.FINALIZE,
            selected_tool="finalize",
            tool_args={},
            expected_outcome="Formatted final response with actionable recommendations.",
            reason="[Fallback Mode: Heuristic Rule] All pipeline stages satisfied.",
            is_terminal=True,
        )

    def decide_next_step(self, state: AgentState) -> str:
        """Adapts the structured PlanDecision to the LangGraph node name."""
        plan_decision = self.plan(state)
        # Store decision on state if mutable
        mapping = {
            AgentActionType.SEARCH_SCHEMES: "matcher",
            AgentActionType.EXTRACT_CITIZEN_PROFILE: "matcher",
            AgentActionType.ASK_CITIZEN_QUESTION: "asker",
            AgentActionType.VERIFY_OFFICIAL_SOURCE: "verifier",
            AgentActionType.COMPARE_ELIGIBILITY: "critic",
            AgentActionType.FINALIZE: "finalize",
        }
        return mapping.get(plan_decision.proposed_action, "finalize")
