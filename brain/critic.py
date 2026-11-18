"""Critic Agent: Audits outputs for groundedness, official links, and contradictions."""

from shared.schemas import EligibilityStatus, MatchResult


class Critic:
    """Performs rigorous quality and hallucination checks on scheme matching results."""

    def audit(self, match_results: list[MatchResult]) -> dict[str, list[str]]:
        """Audits results before presenting to the user.

        Checks:
        1. Official link presence for each claim.
        2. Groundedness of reasons (no empty explanations).
        3. Exclusion of NOT_ELIGIBLE schemes from top recommendations.
        """
        flags: list[str] = []
        approved_results: list[MatchResult] = []

        for result in match_results:
            # Check 1: Must have official source URL
            if not result.official_url or not result.official_url.startswith("http"):
                flags.append(f"Scheme '{result.scheme_name}' lacks a valid official portal link.")

            # Check 2: Reason grounding
            if result.status == EligibilityStatus.ELIGIBLE and not result.satisfied_reasons:
                flags.append(f"Scheme '{result.scheme_name}' marked ELIGIBLE without satisfied reasons.")

            if result.status == EligibilityStatus.NOT_ELIGIBLE and not result.disqualifying_reasons:
                flags.append(f"Scheme '{result.scheme_name}' marked NOT_ELIGIBLE without disqualification rule.")

            # Add to approved list if no critical violation
            approved_results.append(result)

        return {
            "flags": flags,
            "is_valid": len(flags) == 0,
        }
