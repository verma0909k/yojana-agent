"""Tests for experience layer: Hinglish parsing, PDF generation, .ics generation, personas."""

from yojanaagent.experience.actions.calendar_reminders import create_scheme_reminder_ics
from yojanaagent.experience.actions.pdf_filler import generate_application_pdf
from yojanaagent.experience.intake.hinglish import NaturalLanguageIntake
from yojanaagent.experience.personas.demo_profiles import DEMO_PERSONAS, get_student_persona
from yojanaagent.shared.schemas import MatchResult, EligibilityStatus, Occupation


def test_hinglish_parser():
    intake = NaturalLanguageIntake()
    text = "Mai UP ke gaon me kheti karta hu, age 45 saal hai aur BPL card hai"
    profile = intake.parse_user_input(text)

    assert profile.occupation.value == Occupation.FARMER
    assert profile.age.value == 45
    assert profile.is_bpl.value is True
    assert profile.is_rural.value is True


def test_pdf_and_ics_generation():
    student = get_student_persona()
    match = MatchResult(
        scheme_id="test-scheme",
        scheme_name="Test Scholarship",
        status=EligibilityStatus.ELIGIBLE,
        satisfied_reasons=["Student qualification met"],
        official_url="https://scholarships.gov.in",
        documents_required=["Aadhaar", "Marksheet"]
    )

    pdf_path = generate_application_pdf(student, match)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    ics_path = create_scheme_reminder_ics(match)
    assert ics_path.exists()
    assert ics_path.stat().st_size > 0
