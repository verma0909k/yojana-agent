from yojana.models import CitizenProfile, Fact, Source, Occupation


def test_empty_profile_has_all_unknown():
    p = CitizenProfile()
    assert p.known_fields() == {}
    assert "age" in p.unknown_fields()


def test_known_and_low_confidence():
    p = CitizenProfile(
        age=Fact[int](value=58, confidence=0.95, source=Source.DOCUMENT),
        occupation=Fact[Occupation](
            value=Occupation.FARMER, confidence=0.5, source=Source.USER_TEXT
        ),
    )
    assert p.known_fields()["age"] == 58
    assert p.low_confidence_fields() == ["occupation"]