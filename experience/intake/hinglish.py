"""Hinglish, Hindi, and English text intake parser with token-level negation and entity extraction."""

import re
from typing import Any, Optional
from shared.schemas import (
    Category,
    CitizenProfile,
    Fact,
    Gender,
    Occupation,
    Source,
)

# Devanagari digit translation table
DEVA_TO_ASCII = str.maketrans("०१२३४५६७८९", "0123456789")

# Negation words in English, Hinglish, and Hindi
NEGATION_WORDS = {
    "nahi", "nahin", "nhi", "na", "no", "not", "without",
    "नहीं", "नही", "ना", "बिना", "dont", "don't", "never", "mat"
}

# Indian States & UTs mapping with uppercase-sensitive aliases
STATE_ALIASES = {
    "UP": "Uttar Pradesh",
    "uttar pradesh": "Uttar Pradesh",
    "उत्तर प्रदेश": "Uttar Pradesh",
    "MP": "Madhya Pradesh",
    "madhya pradesh": "Madhya Pradesh",
    "मध्य प्रदेश": "Madhya Pradesh",
    "bihar": "Bihar",
    "बिहार": "Bihar",
    "rajasthan": "Rajasthan",
    "राजस्थान": "Rajasthan",
    "maharashtra": "Maharashtra",
    "महाराष्ट्र": "Maharashtra",
    "gujarat": "Gujarat",
    "गुजरात": "Gujarat",
    "punjab": "Punjab",
    "पंजाब": "Punjab",
    "haryana": "Haryana",
    "हरियाणा": "Haryana",
    "delhi": "Delhi",
    "दिल्ली": "Delhi",
    "west bengal": "West Bengal",
    "पश्चिम बंगाल": "West Bengal",
    "karnataka": "Karnataka",
    "कर्नाटक": "Karnataka",
    "tamil nadu": "Tamil Nadu",
    "तमिलनाडु": "Tamil Nadu",
    "andhra pradesh": "Andhra Pradesh",
    "आंध्र प्रदेश": "Andhra Pradesh",
    "telangana": "Telangana",
    "तेलंगाना": "Telangana",
    "kerala": "Kerala",
    "केरल": "Kerala",
    "odisha": "Odisha",
    "ओडिशा": "Odisha",
    "assam": "Assam",
    "असम": "Assam",
    "jharkhand": "Jharkhand",
    "झारखंड": "Jharkhand",
    "chhattisgarh": "Chhattisgarh",
    "छत्तीसगढ़": "Chhattisgarh",
    "uttarakhand": "Uttarakhand",
    "उत्तराखंड": "Uttarakhand",
    "himachal pradesh": "Himachal Pradesh",
    "हिमाचल": "Himachal Pradesh",
    "jammu and kashmir": "Jammu and Kashmir",
    "जम्मू": "Jammu and Kashmir",
    "goa": "Goa",
    "गोवा": "Goa",
}


CLAUSE_BREAKERS = {"par", "but", "lekin", "aur", "and", "magar", "kintu", "parantu", ",", ";", "."}


def _is_token_negated(target_tokens: list[str], words: list[str]) -> bool:
    """Checks if any target token is negated within 3 tokens without crossing clause boundaries."""
    for idx, w in enumerate(words):
        if w in target_tokens:
            # Check backwards up to 3 tokens
            for step in range(1, 4):
                prev_idx = idx - step
                if prev_idx < 0:
                    break
                prev_word = words[prev_idx]
                if prev_word in CLAUSE_BREAKERS:
                    break
                if prev_word in NEGATION_WORDS:
                    return True

            # Check forwards up to 3 tokens
            for step in range(1, 4):
                next_idx = idx + step
                if next_idx >= len(words):
                    break
                next_word = words[next_idx]
                if next_word in CLAUSE_BREAKERS:
                    break
                if next_word in NEGATION_WORDS:
                    return True
    return False


def _find_keyword(text: str, pattern: str) -> bool:
    """Matches pattern using whole-word boundary."""
    return bool(re.search(rf'\b{pattern}\b', text, re.IGNORECASE))


class NaturalLanguageIntake:
    """Extracts demographic facts from conversational messages in English, Hinglish, and Hindi."""

    OCCUPATION_MAP = [
        (["kisan", "kisaan", "farmer", "kheti", "किसान", "खेती"], Occupation.FARMER),
        (["student", "vidyarthi", "chhatra", "विद्यार्थी", "छात्र", "छात्रा"], Occupation.STUDENT),
        (["mazdoor", "labour", "labourer", "worker", "मजदूर", "श्रमिक"], Occupation.LABOURER),
        (["dukan", "vendor", "thela", "दुकान", "ठेला", "फेरीवाला"], Occupation.SELF_EMPLOYED),
        (["self employed", "self_employed", "business", "व्यापार", "व्यवसाय", "स्वरोजगार"], Occupation.SELF_EMPLOYED),
        (["berozgar", "unemployed", "बेरोजगार"], Occupation.UNEMPLOYED),
        (["retired", "retire", "सेवानिवृत्त", "पेंशनर"], Occupation.RETIRED),
        (["homemaker", "housewife", "गृहणी"], Occupation.HOMEMAKER),
    ]

    CATEGORY_MAP = [
        (["general", "सामान्य"], Category.GENERAL),
        (["obc", "ओबीसी", "पिछड़ा"], Category.OBC),
        (["sc", "अनुसूचित जाति"], Category.SC),
        (["st", "अनुसूचित जनजाति"], Category.ST),
        (["ews", "ईडब्ल्यूएस"], Category.EWS),
    ]

    def parse_user_input(self, raw_text: str, existing_profile: Optional[CitizenProfile] = None) -> CitizenProfile:
        """Parses user text and updates/overwrites profile facts with USER_TEXT source."""
        profile = existing_profile or CitizenProfile()
        if not raw_text:
            return profile

        # 1. Normalize Devanagari digits to ASCII
        norm_text = raw_text.translate(DEVA_TO_ASCII)
        text_lower = norm_text.lower()
        words_lower = re.findall(r'[a-zA-Z0-9_\u0900-\u097F]+', text_lower)

        # 2. State Detection (Case-sensitive for acronyms like 'UP', 'MP')
        # Check uppercase UP and MP specifically with word boundaries
        if re.search(r'\bUP\b', norm_text):
            profile.set_fact("state", "Uttar Pradesh", confidence=0.95, source=Source.USER_TEXT)
        elif re.search(r'\bMP\b', norm_text):
            profile.set_fact("state", "Madhya Pradesh", confidence=0.95, source=Source.USER_TEXT)
        else:
            for alias, canonical_state in STATE_ALIASES.items():
                if alias not in ("UP", "MP") and re.search(rf'\b{re.escape(alias.lower())}\b', text_lower):
                    profile.set_fact("state", canonical_state, confidence=0.95, source=Source.USER_TEXT)
                    break

        # 3. Age Extraction (Devanagari keywords + English/Hinglish)
        age_match = re.search(r'\b(?:age|umar|saal|years old|years|उम्र|आयु|वर्ष)\s*(?:is|:|=|हो|\b)?\s*(\d{1,2})\b', text_lower)
        if not age_match:
            age_match = re.search(r'\b(\d{1,2})\s*(?:saal|years|yr|साल|वर्ष)\b', text_lower)
        if age_match:
            try:
                age_val = int(age_match.group(1))
                if 1 <= age_val <= 115:
                    profile.set_fact("age", age_val, confidence=0.95, source=Source.USER_TEXT)
            except Exception:
                pass

        # 4. Gender Extraction (Strict word boundaries to avoid false positives like 'Raman', 'manager')
        female_tokens = ["female", "woman", "women", "mahila", "ladki", "girl", "महिला", "लड़की", "औरत"]
        male_tokens = ["male", "man", "men", "purush", "aadmi", "ladka", "boy", "पुरुष", "आदमी", "लड़का"]

        has_female = any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in female_tokens)
        has_male = any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in male_tokens)

        if has_female:
            negated = _is_token_negated(female_tokens, words_lower)
            if not negated:
                profile.set_fact("gender", Gender.FEMALE, confidence=0.98, source=Source.USER_TEXT)
        elif has_male:
            negated = _is_token_negated(male_tokens, words_lower)
            if not negated:
                profile.set_fact("gender", Gender.MALE, confidence=0.98, source=Source.USER_TEXT)

        # 5. Occupation Extraction (Negation-aware)
        for token_list, occ_enum in self.OCCUPATION_MAP:
            matched_token = next((t for t in token_list if re.search(rf'\b{re.escape(t)}\b', text_lower)), None)
            if matched_token:
                if not _is_token_negated([matched_token], words_lower):
                    profile.set_fact("occupation", occ_enum, confidence=0.95, source=Source.USER_TEXT)
                    break

        # 6. Social Category Extraction
        for token_list, cat_enum in self.CATEGORY_MAP:
            matched_token = next((t for t in token_list if re.search(rf'\b{re.escape(t)}\b', text_lower)), None)
            if matched_token and not _is_token_negated([matched_token], words_lower):
                profile.set_fact("category", cat_enum, confidence=0.95, source=Source.USER_TEXT)
                break

        # 7. Rural / Urban
        rural_tokens = ["village", "gaon", "dehat", "rural", "गांव", "देहात", "ग्रामीण"]
        urban_tokens = ["city", "shahar", "urban", "town", "शहर", "शहरी"]
        if any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in rural_tokens):
            if not _is_token_negated(rural_tokens, words_lower):
                profile.set_fact("is_rural", True, confidence=0.95, source=Source.USER_TEXT)
        elif any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in urban_tokens):
            if not _is_token_negated(urban_tokens, words_lower):
                profile.set_fact("is_rural", False, confidence=0.95, source=Source.USER_TEXT)

        # 8. BPL Status (Strict: plain 'ration card' does NOT imply BPL; APL sets False)
        bpl_tokens = ["bpl", "antyodaya", "below poverty", "garibi rekha", "बीपीएल", "अंत्योदय", "गरीबी रेखा"]
        apl_tokens = ["apl", "एपीएल"]
        poor_tokens = ["gareeb", "poor", "गरीब"]

        has_bpl = any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in bpl_tokens)
        has_apl = any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in apl_tokens)
        has_poor = any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in poor_tokens)

        if has_bpl:
            if _is_token_negated(bpl_tokens, words_lower):
                profile.set_fact("is_bpl", False, confidence=0.95, source=Source.USER_TEXT)
            else:
                profile.set_fact("is_bpl", True, confidence=0.95, source=Source.USER_TEXT)
        elif has_apl:
            profile.set_fact("is_bpl", False, confidence=0.95, source=Source.USER_TEXT)
        elif has_poor and not _is_token_negated(poor_tokens, words_lower):
            profile.set_fact("is_bpl", True, confidence=0.6, source=Source.USER_TEXT)

        # 9. Land Holding: ONLY convert acre/एकड़. Hectare multiplies by 2.471. Ignore bigha/ekad.
        hectare_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hectare|hectares|हेक्टेयर|हैक्टेयर)\b', text_lower)
        acre_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:acre|acres|एकड़|एकड)\b', text_lower)

        if hectare_match:
            val = float(hectare_match.group(1)) * 2.471
            profile.set_fact("land_holding_acres", round(val, 2), confidence=0.95, source=Source.USER_TEXT)
        elif acre_match:
            val = float(acre_match.group(1))
            profile.set_fact("land_holding_acres", val, confidence=0.95, source=Source.USER_TEXT)

        # 10. Annual Income Extraction (lakh, thousand/hazaar, per month multiplier)
        is_monthly = bool(re.search(r'(?:per month|/month|mahina|mahine|har mahine|महीना|प्रति माह|महीने)\b', text_lower))
        multiplier = 12 if is_monthly else 1

        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lac|laakh|लाख)\b', text_lower)
        thousand_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:thousand|k|hazaar|hazar|हजार)\b', text_lower)
        direct_income_match = re.search(r'(?:rs\.?|inr|₹|income|aay|salary|kamata|कमाई|आय|वेतन)\D*(\d{4,8})\b', text_lower)
        post_income_match = re.search(r'\b(\d{4,8})\s*(?:per month|/month|mahina|mahine|har mahine|महीना|प्रति माह|महीने|rupees|rs|salana|kamata|कमाई)\b', text_lower)

        if lakh_match:
            income_val = int(float(lakh_match.group(1)) * 100000 * multiplier)
            profile.set_fact("annual_income", income_val, confidence=0.95, source=Source.USER_TEXT)
        elif thousand_match:
            income_val = int(float(thousand_match.group(1)) * 1000 * multiplier)
            profile.set_fact("annual_income", income_val, confidence=0.95, source=Source.USER_TEXT)
        elif post_income_match:
            income_val = int(post_income_match.group(1)) * multiplier
            profile.set_fact("annual_income", income_val, confidence=0.95, source=Source.USER_TEXT)
        elif direct_income_match:
            income_val = int(direct_income_match.group(1)) * multiplier
            profile.set_fact("annual_income", income_val, confidence=0.95, source=Source.USER_TEXT)

        # 11. Bank Account (khata, bank, passbook)
        bank_tokens = ["bank", "khata", "passbook", "बैंक", "खाता", "पासबुक"]
        if any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in bank_tokens):
            if _is_token_negated(bank_tokens, words_lower):
                profile.set_fact("has_bank_account", False, confidence=0.95, source=Source.USER_TEXT)
            else:
                profile.set_fact("has_bank_account", True, confidence=0.95, source=Source.USER_TEXT)

        # 12. Aadhaar Card
        aadhaar_tokens = ["aadhaar", "aadhar", "adhar", "आधार"]
        if any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in aadhaar_tokens):
            if _is_token_negated(aadhaar_tokens, words_lower):
                profile.set_fact("has_aadhaar", False, confidence=0.95, source=Source.USER_TEXT)
            else:
                profile.set_fact("has_aadhaar", True, confidence=0.95, source=Source.USER_TEXT)

        # 13. Disability Status
        disabled_tokens = ["divyang", "viklang", "disabled", "divyangjan", "दिव्यांग", "विकलांग"]
        if any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in disabled_tokens):
            if _is_token_negated(disabled_tokens, words_lower):
                profile.set_fact("is_disabled", False, confidence=0.95, source=Source.USER_TEXT)
            else:
                profile.set_fact("is_disabled", True, confidence=0.95, source=Source.USER_TEXT)

        # 14. Education Level Mapping
        edu_mappings = [
            (["technical_degree", "btech", "b.tech", "b.e", "btech", "engineering", "बीटेक", "इंजीनियरिंग"], "technical_degree"),
            (["diploma", "iti", "polytechnic", "डिप्लोमा", "आईटीआई"], "diploma"),
            (["postgraduate", "master", "masters", "mtech", "msc", "ma", "mcom", "परास्नातक"], "postgraduate"),
            (["graduate", "degree", "bachelor", "ba", "bsc", "bcom", "स्नातक"], "graduate"),
            (["class 12", "class_12", "12th", "12वीं", "बारहवीं", "inter", "intermediate"], "class_12"),
            (["class 10", "class_10", "10th", "10वीं", "दसवीं", "matric", "highschool"], "class_10"),
        ]
        for tokens, mapped_level in edu_mappings:
            if any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in tokens):
                profile.set_fact("education_level", mapped_level, confidence=0.95, source=Source.USER_TEXT)
                break

        # 15. Fisheries Work
        fisheries_tokens = ["fisheries", "matsya", "machhli", "fish farming", "मत्स्य", "मछली पालन"]
        if any(re.search(rf'\b{re.escape(t)}\b', text_lower) for t in fisheries_tokens):
            if _is_token_negated(fisheries_tokens, words_lower):
                profile.set_fact("works_in_fisheries", False, confidence=0.95, source=Source.USER_TEXT)
            else:
                profile.set_fact("works_in_fisheries", True, confidence=0.95, source=Source.USER_TEXT)

        return profile
