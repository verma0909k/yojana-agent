"""Pre-configured demo personas for fast one-click hackathon evaluation."""

from shared.schemas import (
    Category,
    CitizenProfile,
    Fact,
    Gender,
    Occupation,
    Source,
)


def get_farmer_persona() -> CitizenProfile:
    """Persona 1: Marginal farmer eligible for PM-KISAN, PM-KUSUM."""
    return CitizenProfile(
        age=Fact(value=52, confidence=0.98, source=Source.DOCUMENT),
        gender=Fact(value=Gender.MALE, confidence=1.0, source=Source.DOCUMENT),
        state=Fact(value="Uttar Pradesh", confidence=0.95, source=Source.USER_TEXT),
        district=Fact(value="Varanasi", confidence=0.9, source=Source.USER_TEXT),
        is_rural=Fact(value=True, confidence=0.95, source=Source.USER_TEXT),
        annual_income=Fact(value=120000, confidence=0.9, source=Source.DOCUMENT),
        category=Fact(value=Category.OBC, confidence=0.95, source=Source.DOCUMENT),
        occupation=Fact(value=Occupation.FARMER, confidence=0.99, source=Source.USER_TEXT),
        land_holding_acres=Fact(value=2.4, confidence=0.95, source=Source.DOCUMENT),
        is_bpl=Fact(value=True, confidence=0.9, source=Source.DOCUMENT),
        has_bank_account=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
        has_aadhaar=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
    )


def get_student_persona() -> CitizenProfile:
    """Persona 2: Female college student eligible for Post-Matric & Pragati scholarship."""
    return CitizenProfile(
        age=Fact(value=20, confidence=0.99, source=Source.DOCUMENT),
        gender=Fact(value=Gender.FEMALE, confidence=1.0, source=Source.DOCUMENT),
        state=Fact(value="Bihar", confidence=0.95, source=Source.USER_TEXT),
        district=Fact(value="Patna", confidence=0.9, source=Source.USER_TEXT),
        is_rural=Fact(value=False, confidence=0.9, source=Source.USER_TEXT),
        annual_income=Fact(value=180000, confidence=0.92, source=Source.DOCUMENT),
        category=Fact(value=Category.OBC, confidence=0.98, source=Source.DOCUMENT),
        occupation=Fact(value=Occupation.STUDENT, confidence=0.99, source=Source.USER_TEXT),
        education_level=Fact(value="B.Tech 1st Year", confidence=0.95, source=Source.DOCUMENT),
        has_bank_account=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
        has_aadhaar=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
    )


def get_woman_entrepreneur_persona() -> CitizenProfile:
    """Persona 3: Rural woman artisan/entrepreneur eligible for Lakhpati Didi, Mudra, Ujjwala."""
    return CitizenProfile(
        age=Fact(value=34, confidence=0.95, source=Source.DOCUMENT),
        gender=Fact(value=Gender.FEMALE, confidence=1.0, source=Source.DOCUMENT),
        state=Fact(value="Madhya Pradesh", confidence=0.95, source=Source.USER_TEXT),
        district=Fact(value="Indore", confidence=0.9, source=Source.USER_TEXT),
        is_rural=Fact(value=True, confidence=0.95, source=Source.USER_TEXT),
        annual_income=Fact(value=95000, confidence=0.88, source=Source.DOCUMENT),
        category=Fact(value=Category.SC, confidence=0.98, source=Source.DOCUMENT),
        occupation=Fact(value=Occupation.SELF_EMPLOYED, confidence=0.95, source=Source.USER_TEXT),
        is_bpl=Fact(value=True, confidence=0.95, source=Source.DOCUMENT),
        has_bank_account=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
        has_aadhaar=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
    )


def get_senior_citizen_persona() -> CitizenProfile:
    """Persona 4: Elderly citizen eligible for IGNOAPS Old Age Pension & PM-JAY."""
    return CitizenProfile(
        age=Fact(value=68, confidence=0.99, source=Source.DOCUMENT),
        gender=Fact(value=Gender.MALE, confidence=1.0, source=Source.DOCUMENT),
        state=Fact(value="Rajasthan", confidence=0.95, source=Source.USER_TEXT),
        district=Fact(value="Jaipur", confidence=0.9, source=Source.USER_TEXT),
        is_rural=Fact(value=True, confidence=0.95, source=Source.USER_TEXT),
        annual_income=Fact(value=40000, confidence=0.85, source=Source.USER_TEXT),
        category=Fact(value=Category.GENERAL, confidence=0.9, source=Source.USER_TEXT),
        occupation=Fact(value=Occupation.RETIRED, confidence=0.95, source=Source.USER_TEXT),
        is_bpl=Fact(value=True, confidence=0.98, source=Source.DOCUMENT),
        has_bank_account=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
        has_aadhaar=Fact(value=True, confidence=1.0, source=Source.DOCUMENT),
    )


DEMO_PERSONAS = {
    "Farmer (PM-KISAN / PM-KUSUM eligible)": get_farmer_persona,
    "Student (Post-Matric & AICTE Pragati eligible)": get_student_persona,
    "Woman Entrepreneur (Lakhpati Didi / Mudra eligible)": get_woman_entrepreneur_persona,
    "Senior Citizen (Old Age Pension & PM-JAY eligible)": get_senior_citizen_persona,
}
