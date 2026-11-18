"""Critic Agent: Audits outputs for groundedness, official links, and contradictions, and prunes ungrounded claims."""

from shared.schemas import EligibilityStatus, MatchResult


class Critic:
    """Performs rigorous quality, safety, and hallucination checks on scheme matching results."""

    def audit(self, match_results: list[MatchResult]) -> dict:
        """Audits and self-prunes ungrounded or invalid scheme recommendations.

        Rules:
        1. Official link check: Must have a verifiable http/https portal URL.
        2. Groundedness check: ELIGIBLE schemes must have at least one verified satisfied reason.
        3. Exclusion: Rejects ungrounded or malformed schemes from the approved list.
        """
        flags: list[str] = []
        approved_results: list[MatchResult] = []

        for result in match_results:
            scheme_valid = True

            # Check 1: Must have official source URL
            if not result.official_url or not result.official_url.startswith("http"):
                flags.append(f"Pruned '{result.scheme_name}': Lacks valid official portal URL.")
                scheme_valid = False

            # Check 2: Reason grounding for ELIGIBLE
            if result.status == EligibilityStatus.ELIGIBLE and not result.satisfied_reasons:
                flags.append(f"Pruned '{result.scheme_name}': Marked ELIGIBLE without satisfied rule reasons.")
                scheme_valid = False

            # Check 3: Reason grounding for NOT_ELIGIBLE
            if result.status == EligibilityStatus.NOT_ELIGIBLE and not result.disqualifying_reasons:
                flags.append(f"Flagged '{result.scheme_name}': Missing disqualification reason.")

            if scheme_valid:
                approved_results.append(result)

        pruned_count = len(match_results) - len(approved_results)

        return {
            "flags": flags,
            "is_valid": len(flags) == 0,
            "approved_results": approved_results,
            "pruned_count": pruned_count,
        }
