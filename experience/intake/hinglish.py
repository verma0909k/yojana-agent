"""Hinglish, Hindi, and English text intake parser with negation and income detection."""

import re
from typing import Any
from shared.schemas import Category, CitizenProfile, Fact, Gender, Occupation, Source

NEGATION_WORDS = {"nahi", "nhi", "na", "not", "dont", "don't", "no", "never", "mat", "ni"}


def is_negated(target_word: str, text: str) -> bool:
    """Checks if a keyword is preceded or followed by negation tokens in the phrase."""
    words = re.findall(r'\b\w+\b', text.lower())
    if target_word not in words:
        return False
    idx = words.index(target_word)
    # Check 3 words before and 3 words after
    window = words[max(0, idx - 3): min(len(words), idx + 4)]
    return any(neg in window for neg in NEGATION_WORDS)


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

        # 2. Gender extraction (negation-aware)
        if any(w in text_lower for w in ["female", "woman", "mahila", "ladki", "girl"]):
            if not is_negated("female", text_lower) and not is_negated("mahila", text_lower):
                profile.gender = Fact(value=Gender.FEMALE, confidence=0.98, source=Source.USER_TEXT)
        elif any(w in text_lower for w in ["male", "purush", "aadmi", "ladka", "man", "boy"]):
            if not is_negated("male", text_lower) and not is_negated("purush", text_lower):
                profile.gender = Fact(value=Gender.MALE, confidence=0.98, source=Source.USER_TEXT)

        # 3. Occupation extraction (negation-aware)
        for kw, occ in self.OCCUPATION_MAP.items():
            if kw in text_lower and not is_negated(kw, text_lower):
                profile.occupation = Fact(value=occ, confidence=0.92, source=Source.USER_TEXT)
                break

        # 4. Social Category extraction
        for kw, cat in self.CATEGORY_MAP.items():
            if re.search(rf'\b{kw}\b', text_lower) and not is_negated(kw, text_lower):
                profile.category = Fact(value=cat, confidence=0.95, source=Source.USER_TEXT)
                break

        # 5. Rural / Urban
        if any(w in text_lower for w in ["village", "gaon", "dehat", "rural"]):
            if not is_negated("gaon", text_lower) and not is_negated("rural", text_lower):
                profile.is_rural = Fact(value=True, confidence=0.95, source=Source.USER_TEXT)
        elif any(w in text_lower for w in ["city", "shahar", "urban", "town"]):
            if not is_negated("shahar", text_lower) and not is_negated("urban", text_lower):
                profile.is_rural = Fact(value=False, confidence=0.95, source=Source.USER_TEXT)

        # 6. BPL indicator (negation-aware)
        if any(w in text_lower for w in ["bpl", "ration card", "poor", "gareeb"]):
            if not is_negated("bpl", text_lower) and not is_negated("poor", text_lower):
                profile.is_bpl = Fact(value=True, confidence=0.9, source=Source.USER_TEXT)

        # 7. Land holding
        land_match = re.search(r'(\d+(\.\d+)?)\s*(acre|ekad|bigha)', text_lower)
        if land_match:
            acres = float(land_match.group(1))
            profile.land_holding_acres = Fact(value=acres, confidence=0.9, source=Source.USER_TEXT)

        # 8. Annual Income extraction (e.g. "1.5 lakh", "2 lakh", "150000", "aay 200000")
        income_lakh_match = re.search(r'(\d+(\.\d+)?)\s*(lakh|lac|laakh)', text_lower)
        if income_lakh_match:
            lakh_val = float(income_lakh_match.group(1))
            profile.annual_income = Fact(value=int(lakh_val * 100000), confidence=0.92, source=Source.USER_TEXT)
        else:
            raw_income_match = re.search(r'\b(income|aay|salana|kamata)\D*(\d{4,7})\b', text_lower)
            if raw_income_match:
                profile.annual_income = Fact(value=int(raw_income_match.group(2)), confidence=0.9, source=Source.USER_TEXT)

        return profile
