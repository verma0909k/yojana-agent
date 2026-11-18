"""Deterministic Python Rule Engine for YojanaAgent.
The LLM NEVER decides eligibility. All eligibility calculations happen strictly here.
"""

from typing import Any
from shared.schemas import (
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

        # Evaluate compound OR conditions if primary condition is not satisfied
        if not passed and crit.or_conditions:
            for alt_crit in crit.or_conditions:
                alt_fact = getattr(profile, alt_crit.field, None)
                if alt_fact is not None and alt_fact.known:
                    alt_val = alt_fact.value.value if hasattr(alt_fact.value, "value") else alt_fact.value
                    alt_exp = alt_crit.value.value if hasattr(alt_crit.value, "value") else alt_crit.value
                    if _evaluate_condition(alt_val, alt_crit.operator, alt_exp):
                        passed = True
                        break

        if passed:
            satisfied_reasons.append(crit.description)
        else:
            # Build informative disqualification with actual value and requirement
            if crit.operator == CriterionOperator.IN:
                req_val = ", ".join(str(v) for v in expected_val) if isinstance(expected_val, list) else str(expected_val)
                req_str = f"one of {req_val}"
            elif crit.operator == CriterionOperator.NOT_IN:
                req_val = ", ".join(str(v) for v in expected_val) if isinstance(expected_val, list) else str(expected_val)
                req_str = f"none of {req_val}"
            elif crit.operator == CriterionOperator.EQ:
                req_str = f"{expected_val}"
            elif crit.operator == CriterionOperator.NEQ:
                req_str = f"not {expected_val}"
            elif crit.operator == CriterionOperator.GTE:
                req_str = f">= {expected_val}"
            elif crit.operator == CriterionOperator.LTE:
                req_str = f"<= {expected_val}"
            elif crit.operator == CriterionOperator.IS_TRUE:
                req_str = "True"
            elif crit.operator == CriterionOperator.IS_FALSE:
                req_str = "False"
            else:
                req_str = f"{expected_val}"

            detail = f" (your {crit.field}: {actual_val}; required: {req_str})"
            disqualifying_reasons.append(f"{crit.disqualification_reason}{detail}")

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
        deadline=scheme.deadline,
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
