"""Planner / Orchestrator for YojanaAgent."""

from shared.schemas import AgentState, EligibilityStatus


class Planner:
    """Decides the next action in the autonomous agent loop."""

    def decide_next_step(self, state: AgentState) -> str:
        """Determines the next agent to invoke in the pipeline."""
        # 1. Step limit check
        if state.step_count >= state.max_steps:
            return "finalize"

        # 2. If matching hasn't been run yet, run matching
        if not state.match_results:
            return "matcher"

        # 3. Check if high-value gap question can be asked (up to 2 rounds of asking)
        almost_matches = [m for m in state.match_results if m.status == EligibilityStatus.ALMOST]
        if almost_matches and len(state.pending_questions) < 2:
            return "asker"

        # 4. If matching is complete and verification hasn't run
        if not state.verified_schemes and any(m.status == EligibilityStatus.ELIGIBLE for m in state.match_results):
            return "verifier"

        # 5. Run critic review
        if not state.critic_notes:
            return "critic"

        # 6. Complete
        return "finalize"
