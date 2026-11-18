"""Scheme Retriever for YojanaAgent.
Performs semantic and keyword-based candidate filtering before deterministic evaluation.
"""

from typing import Optional
from knowledge.schemes import load_all_schemes
from shared.schemas import CitizenProfile, Scheme


class SchemeRetriever:
    """Retrieves relevant candidate schemes based on citizen profile and natural queries."""

    def __init__(self, schemes: Optional[list[Scheme]] = None):
        self.schemes = schemes or load_all_schemes()

    def filter_candidates(self, profile: CitizenProfile, query: str = "") -> list[Scheme]:
        """Filters schemes based on demographic signals and query keywords."""
        candidates: list[Scheme] = []
        q = query.lower()

        for scheme in self.schemes:
            score = 0

            # Match on occupation
            if profile.occupation.known:
                occ = profile.occupation.value
                occ_val = occ.value if hasattr(occ, "value") else str(occ)
                if occ_val in scheme.category_tags:
                    score += 3

            # Match on gender
            if profile.gender.known:
                gender_val = profile.gender.value
                gender_str = gender_val.value if hasattr(gender_val, "value") else str(gender_val)
                if gender_str == "female" and any(t in scheme.category_tags for t in ["women", "girl child"]):
                    score += 3

            # Match on BPL / Low Income
            if profile.is_bpl.known and profile.is_bpl.value:
                if "bpl" in scheme.category_tags:
                    score += 2

            # Match on query keywords
            if q:
                keywords = q.split()
                for kw in keywords:
                    if kw in scheme.name.lower() or kw in scheme.description.lower():
                        score += 2
                    if any(kw in tag for tag in scheme.category_tags):
                        score += 2

            # Include scheme if it has relevant overlap or if profile is unspecific
            if score > 0 or not profile.known_fields():
                candidates.append(scheme)

        # If candidates is empty (e.g. general query), return all active schemes
        return candidates if candidates else [s for s in self.schemes if s.is_active]
