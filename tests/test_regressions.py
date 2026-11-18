"""Regression tests for YojanaAgent fixes."""

import pytest
from experience.personas.demo_profiles import (
    get_farmer_persona,
    get_student_persona,
    get_woman_entrepreneur_persona,
    get_senior_citizen_persona,
)
from knowledge.matcher import SchemeMatcher
from knowledge.retriever import SchemeRetriever
from knowledge.rule_engine import evaluate_all
from knowledge.schemes import load_all_schemes
from shared.schemas import EligibilityStatus


def test_fix1_retriever_never_drops_eligible_schemes():
    """FIX 1: Candidate retriever must never exclude active schemes.

    For all 4 personas and diverse queries, the set of ELIGIBLE scheme IDs
    from SchemeMatcher.match must equal the set from evaluate_all directly.
    """
    schemes = load_all_schemes()
    active_schemes = [s for s in schemes if s.is_active]
    matcher = SchemeMatcher(retriever=SchemeRetriever(schemes=schemes))

    personas = [
        get_farmer_persona(),
        get_student_persona(),
        get_woman_entrepreneur_persona(),
        get_senior_citizen_persona(),
    ]

    queries = [
        "",
        "all eligible schemes",
        "mai gaon me rehta hu aur mujhe paise chahiye",
    ]

    for persona in personas:
        # Ground truth: direct evaluation of all active schemes
        direct_results = evaluate_all(profile=persona, schemes=active_schemes)
        expected_eligible = {r.scheme_id for r in direct_results if r.status == EligibilityStatus.ELIGIBLE}

        for q in queries:
            matched_results = matcher.match(profile=persona, query=q)
            actual_eligible = {r.scheme_id for r in matched_results if r.status == EligibilityStatus.ELIGIBLE}

            assert actual_eligible == expected_eligible, (
                f"Mismatch for query '{q}': expected {expected_eligible}, got {actual_eligible}"
            )
