"""Hinglish, Hindi, and English text intake parser."""

import re
from typing import Any
from yojanaagent.shared.schemas import Category, CitizenProfile, Fact, Gender, Occupation, Source


class NaturalLanguageIntake:
    """Parses facts from conversational user messages in Hindi, Hinglish, or English."""

    OCCUPATION_MAP = {
        "kisan": Occupation.FARMER,
        "kisaan": Occupation.FARMER,
        "farmer": Occupation.FARMER,
        "kheti": Occupation.FARMER,
        "student": Occupation.STUDENT,
        "padhai": Occupation.STUDENT,
        "vidyarthi": Occupation.STUDENT,
        "chhatra": Occupation.STUDENT,
        "mazdoor": Occupation.LABOURER,
        "labour": Occupation.LABOURER,
        "worker": Occupation.LABOURER,
        "dukan": Occupation.SELF_EMPLOYED,
        "business": Occupation.SELF_EMPLOYED,
        "vendor": Occupation.SELF_EMPLOYED,
        "thela": Occupation.SELF_EMPLOYED,
        "berozgar": Occupation.UNEMPLOYED,
        "unemployed": Occupation.UNEMPLOYED,
    }

    CATEGORY_MAP = {
        "general": Category.GENERAL,
        "obc": Category.OBC,
        "sc": Category.SC,
        "st": Category.ST,
        "ews": Category.EWS,
    }

    def parse_user_input(self, text: str, existing_profile: CitizenProfile = None) -> CitizenProfile:
        """Enriches citizen profile with facts extracted from free text."""
        profile = existing_profile or CitizenProfile()
        text_lower = text.lower()

        # 1. Age extraction
        age_match = re.search(r'\b(age|umar|saal|years old)\s*(is|:|=)?\s*(\d{1,2})\b', text_lower)
        if not age_match:
            age_match = re.search(r'\b(\d{1,2})\s*(saal|years|yr)\b', text_lower)
        if age_match:
            try:
                age_val = int(age_match.group(3) if age_match.lastindex >= 3 else age_match.group(1))
                if 1 <= age_val <= 100:
                    profile.age = Fact(value=age_val, confidence=0.95, source=Source.USER_TEXT)
            except Exception:
                pass

        # 2. Gender extraction
        if any(w in text_lower for w in ["female", "woman", "mahila", "ladki", "girl"]):
            profile.gender = Fact(value=Gender.FEMALE, confidence=0.98, source=Source.USER_TEXT)
        elif any(w in text_lower for w in ["male", "purush", "aadmi", "ladka", "man", "boy"]):
            profile.gender = Fact(value=Gender.MALE, confidence=0.98, source=Source.USER_TEXT)

        # 3. Occupation extraction
        for kw, occ in self.OCCUPATION_MAP.items():
            if kw in text_lower:
                profile.occupation = Fact(value=occ, confidence=0.92, source=Source.USER_TEXT)
                break

        # 4. Social Category extraction
        for kw, cat in self.CATEGORY_MAP.items():
            if re.search(rf'\b{kw}\b', text_lower):
                profile.category = Fact(value=cat, confidence=0.95, source=Source.USER_TEXT)
                break

        # 5. Rural / Urban
        if any(w in text_lower for w in ["village", "gaon", "dehat", "rural"]):
            profile.is_rural = Fact(value=True, confidence=0.95, source=Source.USER_TEXT)
        elif any(w in text_lower for w in ["city", "shahar", "urban", "town"]):
            profile.is_rural = Fact(value=False, confidence=0.95, source=Source.USER_TEXT)

        # 6. BPL indicator
        if any(w in text_lower for w in ["bpl", "ration card", "poor", "gareeb"]):
            profile.is_bpl = Fact(value=True, confidence=0.9, source=Source.USER_TEXT)

        # 7. Land holding
        land_match = re.search(r'(\d+(\.\d+)?)\s*(acre|ekad|bigha)', text_lower)
        if land_match:
            acres = float(land_match.group(1))
            profile.land_holding_acres = Fact(value=acres, confidence=0.9, source=Source.USER_TEXT)

        return profile
