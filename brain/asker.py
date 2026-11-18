"""Gap-Asking Agent: Identifies the single most impactful missing fact that could unlock schemes."""

from collections import Counter
from typing import Optional
from shared.schemas import CitizenProfile, EligibilityStatus, MatchResult

QUESTION_TEMPLATES_EN = {
    "is_bpl": "Do you hold a Below Poverty Line (BPL) or Antyodaya ration card?",
    "category": "Which social category do you belong to? (General, OBC, SC, ST, EWS)",
    "occupation": "What is your primary occupation or source of livelihood?",
    "annual_income": "What is your approximate total family income per year?",
    "age": "Could you please share your age?",
    "gender": "What is your gender (Male / Female / Other)?",
    "is_rural": "Do you live in a rural village or an urban city area?",
    "land_holding_acres": "How many acres of agricultural land do you or your family own?",
    "is_disabled": "Do you have any benchmark disability?",
    "has_bank_account": "Do you have an active bank account in your name?",
    "has_aadhaar": "Do you possess an Aadhaar card?",
    "education_level": "What is your highest completed or ongoing education qualification?",
}

QUESTION_TEMPLATES_HI = {
    "is_bpl": "क्या आपके पास बीपीएल (BPL) या अंत्योदय राशन कार्ड है?",
    "category": "आप किस सामाजिक वर्ग से आते हैं? (General, OBC, SC, ST, EWS)",
    "occupation": "आपका मुख्य व्यवसाय या आजीविका का साधन क्या है?",
    "annual_income": "आपकी वार्षिक पारिवारिक आय (लगभग) कितनी है?",
    "age": "कृपया अपनी आयु (उम्र) बताएं?",
    "gender": "आपका लिंग क्या है (पुरुष / महिला / अन्य)?",
    "is_rural": "क्या आप ग्रामीण क्षेत्र (गांव) में रहते हैं या शहरी क्षेत्र में?",
    "land_holding_acres": "आपके पास कितनी एकड़ कृषि भूमि है?",
    "is_disabled": "क्या आप दिव्यांगजन हैं?",
    "has_bank_account": "क्या आपका स्वयं का बैंक खाता है?",
    "has_aadhaar": "क्या आपके पास आधार कार्ड उपलब्ध है?",
    "education_level": "आपकी उच्चतम शिक्षा योग्यता क्या है?",
}


class GapAsker:
    """Calculates info-gain over missing fields and produces high-value questions."""

    def find_highest_impact_gap(self, match_results: list[MatchResult]) -> Optional[str]:
        """Finds the field whose absence is blocking the highest number of ALMOST schemes."""
        almost_matches = [m for m in match_results if m.status == EligibilityStatus.ALMOST]
        if not almost_matches:
            return None

        missing_counter = Counter()
        for m in almost_matches:
            for field in m.missing_fields:
                missing_counter[field] += 1

        if not missing_counter:
            return None

        # Return the field that appears most frequently
        top_field, count = missing_counter.most_common(1)[0]
        return top_field

    def generate_question(self, field_name: str, language: str = "en") -> str:
        """Generates natural question in user language."""
        templates = QUESTION_TEMPLATES_HI if language == "hi" else QUESTION_TEMPLATES_EN
        return templates.get(
            field_name,
            f"Please provide your {field_name.replace('_', ' ')}."
        )
