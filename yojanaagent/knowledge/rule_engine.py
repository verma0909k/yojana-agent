"""Deterministic Python Rule Engine for YojanaAgent.
The LLM NEVER decides eligibility. All eligibility calculations happen strictly here.
"""

from typing import Any
from yojanaagent.shared.schemas import (
    CitizenProfile,
    Criterion,
    CriterionOperator,
    EligibilityStatus,
    MatchResult,
    Scheme,
)


def _evaluate_condition(actual: Any, op: CriterionOperator, expected: Any) -> bool:
    """Evaluates an atomic criterion condition."""
    if op == CriterionOperator.EQ:
        return actual == expected
    elif op == CriterionOperator.NEQ:
        return actual != expected
    elif op == CriterionOperator.GTE:
        return actual >= expected
    elif op == CriterionOperator.LTE:
        return actual <= expected
    elif op == CriterionOperator.IN:
        if isinstance(expected, list):
            return actual in expected
        return str(actual) in str(expected)
    elif op == CriterionOperator.NOT_IN:
        if isinstance(expected, list):
            return actual not in expected
        return str(actual) not in str(expected)
    elif op == CriterionOperator.IS_TRUE:
        return bool(actual) is True
    elif op == CriterionOperator.IS_FALSE:
        return bool(actual) is False
    return False


def evaluate_scheme(profile: CitizenProfile, scheme: Scheme) -> MatchResult:
    """Evaluates a CitizenProfile against a Scheme deterministically.

    Returns:
        - NOT_ELIGIBLE: At least one criterion is explicitly violated by known facts.
        - ALMOST: No disqualifications, but one or more required fields are unknown.
        - ELIGIBLE: All criteria are fully evaluated and satisfied.
    """
    satisfied_reasons: list[str] = []
    missing_fields: list[str] = []
    disqualifying_reasons: list[str] = []

    for crit in scheme.criteria:
        fact = getattr(profile, crit.field, None)

        # 1. Check if fact is unknown
        if fact is None or not fact.known:
            missing_fields.append(crit.field)
            continue

        # 2. Evaluate known fact
        actual_val = fact.value
        # For enums, compare value directly if needed
        if hasattr(actual_val, "value"):
            actual_val = actual_val.value
        expected_val = crit.value
        if hasattr(expected_val, "value"):
            expected_val = expected_val.value

        passed = _evaluate_condition(actual_val, crit.operator, expected_val)

        if passed:
            satisfied_reasons.append(crit.description)
        else:
            disqualifying_reasons.append(crit.disqualification_reason)

    # 3. Determine Final Verdict
    if disqualifying_reasons:
        status = EligibilityStatus.NOT_ELIGIBLE
        deciding_rule = disqualifying_reasons[0]
    elif missing_fields:
        status = EligibilityStatus.ALMOST
        deciding_rule = f"Missing required info: {', '.join(missing_fields)}"
    else:
        status = EligibilityStatus.ELIGIBLE
        deciding_rule = "All criteria satisfied"

    return MatchResult(
        scheme_id=scheme.id,
        scheme_name=scheme.name,
        status=status,
        satisfied_reasons=satisfied_reasons,
        missing_fields=missing_fields,
        disqualifying_reasons=disqualifying_reasons,
        deciding_rule=deciding_rule,
        benefit_summary=scheme.benefits,
        official_url=scheme.official_url,
        documents_required=scheme.documents_required,
    )


def evaluate_all(profile: CitizenProfile, schemes: list[Scheme]) -> list[MatchResult]:
    """Evaluates profile against a list of schemes and returns ranked results."""
    results = [evaluate_scheme(profile, s) for s in schemes]

    # Rank: ELIGIBLE first, then ALMOST, then NOT_ELIGIBLE
    priority = {
        EligibilityStatus.ELIGIBLE: 0,
        EligibilityStatus.ALMOST: 1,
        EligibilityStatus.NOT_ELIGIBLE: 2,
    }
    return sorted(results, key=lambda r: priority[r.status])
