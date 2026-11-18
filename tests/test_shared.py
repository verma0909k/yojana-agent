"""Tests for shared schemas and confidence tracking."""

from shared.schemas import CitizenProfile, Fact, Gender, Occupation, Source, Scheme, Criterion, CriterionOperator


def test_profile_creation_and_facts():
    profile = CitizenProfile()
    assert profile.known_fields() == {}
    assert "age" in profile.unknown_fields()

    profile.set_fact("age", 25, confidence=0.9, source=Source.DOCUMENT)
    assert profile.known_fields()["age"] == 25
    assert "age" not in profile.unknown_fields()


def test_confidence_threshold_filtering():
    profile = CitizenProfile()
    profile.set_fact("annual_income", 150000, confidence=0.5, source=Source.USER_TEXT)
    assert "annual_income" in profile.low_confidence_fields(threshold=0.7)
