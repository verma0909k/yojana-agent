"""Gap-Asking and Conflict Resolution Agent for YojanaAgent.

Identifies the single most impactful missing fact blocking schemes,
and leverages the LLM to spot conflicts between self-reported profile facts
and vault documents, converting them into actionable clarification questions.
"""

from __future__ import annotations

from collections import Counter
import json
import logging
from typing import Any, Optional

from brain.llm_client import LLMClient, mask_aadhaar
from shared.schemas import (
    CitizenProfile,
    DocumentExtraction,
    EligibilityStatus,
    MatchResult,
    ProfileConflictItem,
    StoredDocumentMetadata,
)

logger = logging.getLogger(__name__)

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
    "works_in_fisheries": "Are you actively engaged in fisheries, aquaculture, or allied fishing activities?",
    "is_shg_member": "Are you an active member of a Self-Help Group (SHG) or Mahila Mandal?",
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
    "works_in_fisheries": "क्या आप मत्स्य पालन (मछली पालन) या संबंधित गतिविधियों से जुड़े हैं?",
    "is_shg_member": "क्या आप किसी स्वयं सहायता समूह (SHG) या महिला मंडल की सदस्य हैं?",
}


class GapAsker:
    """Calculates info-gain over missing fields and produces high-value questions,
    prioritizing conflict resolution between stated facts and uploaded documents.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def spot_profile_conflicts(
        self,
        profile: CitizenProfile,
        documents: list[Any],
    ) -> list[ProfileConflictItem]:
        """Uses LLM to detect contradictions between self-reported facts and vault documents,
        formulating clarification questions in English and Hindi.
        """
        if not documents:
            return []

        doc_summaries = []
        for d in documents:
            if isinstance(d, StoredDocumentMetadata):
                ext = d.extracted_data
                doc_summaries.append({
                    "doc_type": ext.doc_type,
                    "holder_name": ext.holder_name,
                    "income_amount": ext.income_amount,
                    "date_of_birth": ext.date_of_birth,
                    "id_last4": ext.id_last4,
                })
            elif isinstance(d, DocumentExtraction):
                doc_summaries.append({
                    "doc_type": d.doc_type,
                    "holder_name": d.holder_name,
                    "income_amount": d.income_amount,
                    "date_of_birth": d.date_of_birth,
                    "id_last4": d.id_last4,
                })
            elif isinstance(d, dict):
                doc_summaries.append(d)

        stated_facts = profile.known_fields()
        masked_facts = json.loads(mask_aadhaar(json.dumps(stated_facts, default=str)))
        masked_docs = json.loads(mask_aadhaar(json.dumps(doc_summaries, default=str)))

        # Rule-based fast check for income conflict
        conflicts: list[ProfileConflictItem] = []
        if profile.annual_income.known:
            stated_inc = profile.annual_income.value
            for d in doc_summaries:
                doc_inc = d.get("income_amount")
                if doc_inc is not None and abs(stated_inc - doc_inc) > 20000:
                    conflicts.append(
                        ProfileConflictItem(
                            field_name="annual_income",
                            stated_value=f"₹{stated_inc:,}",
                            document_value=f"₹{doc_inc:,}",
                            document_source=d.get("doc_type", "Income Certificate"),
                            conflict_severity="HIGH",
                            clarification_question_en=(
                                f"Your profile states an annual income of ₹{stated_inc:,}, but your uploaded "
                                f"{d.get('doc_type', 'Income Certificate')} states ₹{doc_inc:,}. "
                                "Which income figure should we consider for eligibility?"
                            ),
                            clarification_question_hi=(
                                f"आपके प्रोफाइल में वार्षिक आय ₹{stated_inc:,} बताई गई है, लेकिन आपके अपलोड किए गए "
                                f"{d.get('doc_type', 'आय प्रमाण पत्र')} में ₹{doc_inc:,} दर्ज है। "
                                "पात्रता के लिए हमें कौन सी आय माननी चाहिए?"
                            ),
                        )
                    )

        # If LLM is available, perform comprehensive cross-checking
        if self.llm.is_available():
            prompt = f"""Compare the citizen's self-reported profile facts with their uploaded documents.
Identify any clear contradictions (e.g. name variations, income discrepancies, category mismatches).

Self-Reported Facts:
{json.dumps(masked_facts, ensure_ascii=False, indent=2)}

Uploaded Document Facts:
{json.dumps(masked_docs, ensure_ascii=False, indent=2)}

If any conflict exists, return a list of ProfileConflictItem objects.
Each item must include respectful clarification questions in both English and Hindi.
If no conflicts exist, return an empty list.
"""
            try:
                class ConflictReport(CitizenProfile.__class__):
                    pass
                from pydantic import BaseModel
                class ConflictBundle(BaseModel):
                    items: list[ProfileConflictItem] = []

                bundle, _ = self.llm.generate_structured(
                    prompt=prompt,
                    schema_class=ConflictBundle,
                    system_prompt="You detect inconsistencies in citizen identity and entitlement records.",
                )
                if bundle and bundle.items:
                    # Merge while avoiding duplicate field conflicts
                    existing_fields = {c.field_name for c in conflicts}
                    for itm in bundle.items:
                        if itm.field_name not in existing_fields:
                            conflicts.append(itm)
                            existing_fields.add(itm.field_name)
            except Exception as e:
                logger.warning("LLM profile conflict check error: %s", e)

        return conflicts

    def find_highest_impact_gap(
        self,
        match_results: list[MatchResult],
        exclude_fields: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Finds the field whose absence is blocking the highest number of ALMOST schemes, skipping exclude_fields."""
        almost_matches = [m for m in match_results if m.status == EligibilityStatus.ALMOST]
        if not almost_matches:
            return None

        exclude_set = set(exclude_fields or [])
        missing_counter = Counter()
        for m in almost_matches:
            for field in m.missing_fields:
                if field not in exclude_set:
                    missing_counter[field] += 1

        if not missing_counter:
            return None

        top_field, _ = missing_counter.most_common(1)[0]
        return top_field

    def generate_question(self, field_name: str, language: str = "en") -> str:
        """Generates natural question in user language."""
        templates = QUESTION_TEMPLATES_HI if language == "hi" else QUESTION_TEMPLATES_EN
        return templates.get(
            field_name,
            f"Please provide your {field_name.replace('_', ' ')}."
        )

    def get_next_question(
        self,
        match_results: list[MatchResult],
        profile: CitizenProfile,
        documents: Optional[list[Any]] = None,
        exclude_fields: Optional[list[str]] = None,
        language: str = "en",
    ) -> Optional[dict[str, Any]]:
        """Returns the highest priority question for the citizen.
        Prioritizes high-severity document/profile conflicts before asking missing facts.
        """
        # 1. First priority: Check for document vs profile conflicts
        conflicts = self.spot_profile_conflicts(profile, documents or [])
        if conflicts:
            top_conflict = conflicts[0]
            question = (
                top_conflict.clarification_question_hi
                if language == "hi"
                else top_conflict.clarification_question_en
            )
            return {
                "type": "CONFLICT_RESOLUTION",
                "field_name": top_conflict.field_name,
                "question": question,
                "conflict": top_conflict.model_dump(),
                "severity": top_conflict.conflict_severity,
            }

        # 2. Second priority: Highest impact missing information gap
        gap_field = self.find_highest_impact_gap(match_results, exclude_fields=exclude_fields)
        if gap_field:
            return {
                "type": "MISSING_FACT",
                "field_name": gap_field,
                "question": self.generate_question(gap_field, language=language),
                "severity": "NORMAL",
            }

        return None
