"""Scheme Retriever for YojanaAgent.
Performs whole-word keyword and demographic relevance scoring without excluding any active scheme.
"""

import re
import string
from typing import Optional
from knowledge.schemes import load_all_schemes
from shared.schemas import CitizenProfile, Scheme

# Stopwords in English and Hinglish to ignore during keyword scoring
STOPWORDS = {
    "me", "ke", "hai", "aur", "all", "the", "and", "for", "with", "from",
    "you", "are", "this", "that", "ka", "ki", "ko", "se", "hu", "ho", "mein",
    "par", "bhi", "kya", "mai", "mera", "meri", "hum", "yeh", "woh", "kar",
    "kare", "karna", "tha", "thi", "the"
}


def _tokenize(text: str) -> set[str]:
    """Extracts whole-word tokens (lowercase, stripped punctuation, >= 3 chars, not in stopwords)."""
    if not text:
        return set()
    # Replace punctuation with spaces and split into words
    words = re.findall(r'\b[a-zA-Z0-9_]+\b', text.lower())
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}


class SchemeRetriever:
    """Retrieves all active schemes ordered by relevance score based on citizen profile and natural queries."""

    def __init__(self, schemes: Optional[list[Scheme]] = None):
        self.schemes = schemes or load_all_schemes()

    def filter_candidates(self, profile: CitizenProfile, query: str = "") -> list[Scheme]:
        """Scores and returns ALL active schemes ordered by relevance. Never drops active schemes."""
        active_schemes = [s for s in self.schemes if s.is_active]
        query_tokens = _tokenize(query)

        scored_schemes: list[tuple[float, Scheme]] = []

        for scheme in active_schemes:
            score = 0.0

            # 1. Demographic Relevance Scoring
            if profile.occupation.known:
                occ = profile.occupation.value
                occ_val = occ.value if hasattr(occ, "value") else str(occ)
                if occ_val in scheme.category_tags:
                    score += 5.0

            if profile.gender.known:
                gender_val = profile.gender.value
                gender_str = gender_val.value if hasattr(gender_val, "value") else str(gender_val)
                if gender_str == "female" and any(t in scheme.category_tags for t in ["women", "girl child"]):
                    score += 4.0

            if profile.is_bpl.known and profile.is_bpl.value:
                if "bpl" in scheme.category_tags:
                    score += 3.0

            if profile.is_rural.known and profile.is_rural.value:
                if "rural" in scheme.category_tags:
                    score += 2.0

            # 2. Query Keyword Matching (Whole-word tokens)
            if query_tokens:
                name_tokens = _tokenize(scheme.name)
                desc_tokens = _tokenize(scheme.description)
                tag_tokens = set()
                for tag in scheme.category_tags:
                    tag_tokens.update(_tokenize(tag))

                # Weight name matches highest, then tags, then description
                name_matches = query_tokens.intersection(name_tokens)
                tag_matches = query_tokens.intersection(tag_tokens)
                desc_matches = query_tokens.intersection(desc_tokens)

                score += len(name_matches) * 4.0
                score += len(tag_matches) * 2.0
                score += len(desc_matches) * 1.0

            scored_schemes.append((score, scheme))

        # Sort descending by relevance score (stable sort preserving default order for ties)
        scored_schemes.sort(key=lambda x: x[0], reverse=True)
        return [scheme for _, scheme in scored_schemes]
