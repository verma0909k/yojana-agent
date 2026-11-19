"""Scheme Matcher supporting both LLM-grounded policy evaluation (default)
and deterministic rule-table execution (when DECISION_MODE=rules).
"""

from typing import Optional

from brain.llm_client import LLMClient, LLMUnavailableError
from knowledge.llm_matcher import LLMMatcher
from knowledge.retriever import SchemeRetriever
from knowledge.rule_engine import evaluate_all
from shared.config import DECISION_MODE
from shared.schemas import (
    CitizenProfile,
    EligibilityStatus,
    GroundedEligibilityVerdict,
    MatchResult,
    Scheme,
)


class SchemeMatcher:
    """Orchestrates candidate scheme retrieval and eligibility determination."""

    def __init__(
        self,
        retriever: Optional[SchemeRetriever] = None,
        llm_matcher: Optional[LLMMatcher] = None,
        decision_mode: Optional[str] = None,
    ):
        self.retriever = retriever or SchemeRetriever()
        self.llm_matcher = llm_matcher or LLMMatcher()
        self.decision_mode = (decision_mode or DECISION_MODE).lower()

    def match(self, profile: CitizenProfile, query: str = "") -> list[MatchResult]:
        """Runs candidate retrieval followed by LLM-first (or rules fallback) evaluation."""
        candidates: list[Scheme] = self.retriever.filter_candidates(profile=profile, query=query)

        # 1. Deterministic rule-table mode (only when explicitly configured)
        if self.decision_mode == "rules":
            return evaluate_all(profile=profile, schemes=candidates)

        # 2. LLM-first grounded evaluation mode (Default)
        if not self.llm_matcher.llm.is_available():
            raise LLMUnavailableError(
                "LLM is unavailable for eligibility determination. "
                "Configure GOOGLE_API_KEY / ANTHROPIC_API_KEY in .env or set DECISION_MODE=rules."
            )

        verdicts = self.llm_matcher.evaluate_all_grounded(profile=profile, schemes=candidates)
        return [self._verdict_to_match_result(v, candidates) for v in verdicts]

    @staticmethod
    def _verdict_to_match_result(
        verdict: GroundedEligibilityVerdict, candidates: list[Scheme]
    ) -> MatchResult:
        """Converts GroundedEligibilityVerdict to canonical MatchResult."""
        scheme_map = {s.id: s for s in candidates}
        scheme_obj = scheme_map.get(verdict.scheme_id)

        status_str = verdict.status.upper()
        if status_str == "ELIGIBLE":
            status = EligibilityStatus.ELIGIBLE
        elif status_str == "NOT_ELIGIBLE":
            status = EligibilityStatus.NOT_ELIGIBLE
        else:
            status = EligibilityStatus.ALMOST

        deciding_rule = None
        if verdict.needs_review or status_str == "NEEDS_REVIEW":
            deciding_rule = f"NEEDS_REVIEW: {verdict.audit_notes or 'Flagged for human verification'}"
        elif verdict.evidence_quotes:
            deciding_rule = f"Evidence: \"{verdict.evidence_quotes[0]}\""

        return MatchResult(
            scheme_id=verdict.scheme_id,
            scheme_name=verdict.scheme_name,
            status=status,
            satisfied_reasons=verdict.satisfied_reasons,
            missing_fields=verdict.missing_fields,
            disqualifying_reasons=verdict.disqualifying_reasons,
            deciding_rule=deciding_rule,
            benefit_summary=verdict.benefit_summary or (scheme_obj.benefits if scheme_obj else ""),
            official_url=scheme_obj.official_url if scheme_obj else "",
            documents_required=verdict.documents_required or (scheme_obj.documents_required if scheme_obj else []),
            deadline=scheme_obj.deadline if scheme_obj else None,
        )
