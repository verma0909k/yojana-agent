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


def test_fix2_overmatching_rules_tightened():
    """FIX 2: Rules that overmatched are tightened with specific criteria."""
    schemes_dict = {s.id: s for s in load_all_schemes()}

    # 1. PM-Matsya Sampada requires works_in_fisheries
    farmer = get_farmer_persona()  # works_in_fisheries is False
    res_matsya = evaluate_all(profile=farmer, schemes=[schemes_dict["pm-matsya-sampada"]])[0]
    assert res_matsya.status == EligibilityStatus.NOT_ELIGIBLE
    assert "fisheries" in res_matsya.deciding_rule.lower()

    # 2. AICTE Pragati requires technical_degree or diploma
    student = get_student_persona()  # education_level is "technical_degree"
    res_pragati = evaluate_all(profile=student, schemes=[schemes_dict["aicte-pragati-scholarship"]])[0]
    assert res_pragati.status == EligibilityStatus.ELIGIBLE

    non_tech_student = get_student_persona()
    non_tech_student.set_fact("education_level", "class_10")
    res_pragati_fail = evaluate_all(profile=non_tech_student, schemes=[schemes_dict["aicte-pragati-scholarship"]])[0]
    assert res_pragati_fail.status == EligibilityStatus.NOT_ELIGIBLE

    # 3. Lakhpati Didi requires is_shg_member
    woman = get_woman_entrepreneur_persona()  # is_shg_member is True
    res_lakhpati = evaluate_all(profile=woman, schemes=[schemes_dict["lakhpati-didi"]])[0]
    assert res_lakhpati.status == EligibilityStatus.ELIGIBLE

    non_shg_woman = get_woman_entrepreneur_persona()
    non_shg_woman.set_fact("is_shg_member", False)
    res_lakhpati_fail = evaluate_all(profile=non_shg_woman, schemes=[schemes_dict["lakhpati-didi"]])[0]
    assert res_lakhpati_fail.status == EligibilityStatus.NOT_ELIGIBLE

    # 4. PM-KISAN requires land_holding_acres >= 0.01
    landless_farmer = get_farmer_persona()
    landless_farmer.set_fact("land_holding_acres", 0.0)
    res_kisan_fail = evaluate_all(profile=landless_farmer, schemes=[schemes_dict["pm-kisan"]])[0]
    assert res_kisan_fail.status == EligibilityStatus.NOT_ELIGIBLE


def test_fix3_disqualification_messages_informative():
    """FIX 3: Disqualification messages append actual value and requirement.

    Senior persona vs PM-Mudra produces a reason containing 'retired' and not 'salaried'.
    """
    schemes_dict = {s.id: s for s in load_all_schemes()}
    senior = get_senior_citizen_persona()
    res_mudra = evaluate_all(profile=senior, schemes=[schemes_dict["pm-mudra"]])[0]

    assert res_mudra.status == EligibilityStatus.NOT_ELIGIBLE
    assert "retired" in res_mudra.deciding_rule
    assert "salaried" not in res_mudra.deciding_rule


def test_fix4_json_single_source_of_truth(tmp_path):
    """FIX 4: JSON files are the single source of truth; corruption fails loudly."""
    import json
    from shared.config import SCHEMES_DIR

    # 1. Total loaded count equals number of .json files
    json_count = len(list(SCHEMES_DIR.glob("*.json")))
    loaded = load_all_schemes()
    assert len(loaded) == json_count

    # 2. Edit a temp copy of a scheme and confirm changes are loaded
    sample_file = list(SCHEMES_DIR.glob("*.json"))[0]
    data = json.loads(sample_file.read_text(encoding="utf-8"))
    data["name"] = "Modified Test Scheme Name"

    temp_dir = tmp_path / "schemes"
    temp_dir.mkdir()
    temp_file = temp_dir / sample_file.name
    temp_file.write_text(json.dumps(data), encoding="utf-8")

    temp_loaded = load_all_schemes(directory=temp_dir)
    assert len(temp_loaded) == 1
    assert temp_loaded[0].name == "Modified Test Scheme Name"

    # 3. Broken JSON syntax raises clear ValueError naming the file
    bad_json = temp_dir / "bad_syntax.json"
    bad_json.write_text("{ broken json: true, ", encoding="utf-8")
    with pytest.raises(ValueError, match="Failed to parse JSON in 'bad_syntax.json'"):
        load_all_schemes(directory=temp_dir)
    bad_json.unlink()

    # 4. Schema validation failure raises clear ValueError naming the file
    bad_schema = temp_dir / "bad_schema.json"
    bad_schema.write_text(json.dumps({"id": "incomplete"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Scheme validation failed for 'bad_schema.json'"):
        load_all_schemes(directory=temp_dir)


def test_fix5_hinglish_intake_parser():
    """FIX 5: Hinglish/Hindi intake parser with negation and entity extraction (18 test phrases)."""
    from experience.intake.hinglish import NaturalLanguageIntake
    from shared.schemas import CitizenProfile, Gender

    intake = NaturalLanguageIntake()

    # 1. "BPL card nahi hai" -> is_bpl is False
    p1 = intake.parse_user_input("BPL card nahi hai")
    assert p1.is_bpl.value is False

    # 2. "no bank account" -> has_bank_account is False
    p2 = intake.parse_user_input("I have no bank account")
    assert p2.has_bank_account.value is False

    # 3. "bank khata nahi" -> has_bank_account is False
    p3 = intake.parse_user_input("mere paas bank khata nahi hai")
    assert p3.has_bank_account.value is False

    # 4. "आधार नहीं है" -> has_aadhaar is False
    p4 = intake.parse_user_input("मेरे पास आधार नहीं है")
    assert p4.has_aadhaar.value is False

    # 5. Plain "ration card" must NOT imply BPL
    p5 = intake.parse_user_input("mere paas ration card hai")
    assert p5.is_bpl.known is False

    # 6. "APL card" sets is_bpl False
    p6 = intake.parse_user_input("mere paas APL card hai")
    assert p6.is_bpl.value is False

    # 7. "gareeb" sets is_bpl True with confidence 0.6
    p7 = intake.parse_user_input("mai gareeb hu")
    assert p7.is_bpl.value is True
    assert p7.is_bpl.confidence == 0.6

    # 8. Word boundaries prevent false positive on "Raman" or "manager"
    p8 = intake.parse_user_input("My manager Raman is working")
    assert p8.gender.known is False

    # 9. Female extraction with word boundaries
    p9 = intake.parse_user_input("I am a woman from Bihar")
    assert p9.gender.value == Gender.FEMALE

    # 10. Land: hectare converts to acre (* 2.471)
    p10 = intake.parse_user_input("mere paas 2 hectare jameen hai")
    assert p10.land_holding_acres.value == 4.94

    # 11. Land: bigha is NOT converted to acre (remains unknown for asker)
    p11 = intake.parse_user_input("mere paas 5 bigha jameen hai")
    assert p11.land_holding_acres.known is False

    # 12. Income: lakh extraction
    p12 = intake.parse_user_input("meri salana aay 1.5 lakh hai")
    assert p12.annual_income.value == 150000

    # 13. Income: per month extraction multiplies by 12
    p13 = intake.parse_user_input("mai 10000 per month kamata hu")
    assert p13.annual_income.value == 120000

    # 14. State: uppercase UP matches Uttar Pradesh
    p14 = intake.parse_user_input("mai UP se hu aur sign up kar raha hu")
    assert p14.state.value == "Uttar Pradesh"

    # 15. State: lowercase "up" does not match Uttar Pradesh
    p15 = intake.parse_user_input("pick it up")
    assert p15.state.known is False

    # 16. Devanagari digits and age keywords: "उम्र ४५ साल है"
    p16 = intake.parse_user_input("मेरी उम्र ४५ साल है")
    assert p16.age.value == 45

    # 17. Education level: BTech maps to technical_degree
    p17 = intake.parse_user_input("mai BTech 1st year student hu")
    assert p17.education_level.value == "technical_degree"

    # 18. Disability & Fisheries with negation:
    p18 = intake.parse_user_input("mai divyang nahi hu par matsya palan karta hu")
    assert p18.is_disabled.value is False
    assert p18.works_in_fisheries.value is True




