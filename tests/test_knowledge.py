"""Tests for knowledge layer: Rule Engine, Retriever, Verifier, Schemes."""

from yojanaagent.knowledge.schemes import load_all_schemes
from yojanaagent.knowledge.rule_engine import evaluate_scheme, evaluate_all
from yojanaagent.shared.schemas import (
    CitizenProfile,
    EligibilityStatus,
    Fact,
    Gender,
    Occupation,
    Source,
)


def test_schemes_loaded_count():
    schemes = load_all_schemes()
    assert len(schemes) >= 20


def test_rule_engine_eligible_and_disqualified():
    schemes = {s.id: s for s in load_all_schemes()}
    pm_kisan = schemes["pm-kisan"]

    # 1. Unknown facts -> ALMOST
    empty_profile = CitizenProfile()
    res1 = evaluate_scheme(empty_profile, pm_kisan)
    assert res1.status == EligibilityStatus.ALMOST
    assert "occupation" in res1.missing_fields

    # 2. Student occupation -> NOT_ELIGIBLE
    student_profile = CitizenProfile(
        occupation=Fact(value=Occupation.STUDENT, confidence=1.0, source=Source.USER_TEXT),
        has_bank_account=Fact(value=True, confidence=1.0, source=Source.USER_TEXT),
        has_aadhaar=Fact(value=True, confidence=1.0, source=Source.USER_TEXT),
    )
    res2 = evaluate_scheme(student_profile, pm_kisan)
    assert res2.status == EligibilityStatus.NOT_ELIGIBLE
    assert "not farmer" in res2.deciding_rule

    # 3. Legitimate Farmer -> ELIGIBLE
    farmer_profile = CitizenProfile(
        occupation=Fact(value=Occupation.FARMER, confidence=1.0, source=Source.DOCUMENT),
        has_bank_account=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
        has_aadhaar=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
    )
    res3 = evaluate_scheme(farmer_profile, pm_kisan)
    assert res3.status == EligibilityStatus.ELIGIBLE
