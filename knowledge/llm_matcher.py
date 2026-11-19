"""LLM-Driven Scheme Matcher with Strict Grounding, Source Evidence Quotes,
Two-Pass Reviewer Auditing, and Empathetic Rejection Explanations.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from brain.llm_client import LLMClient, mask_aadhaar
from knowledge.schemes.data import load_all_schemes
from knowledge.semantic_search import SemanticSearchEngine
from shared.config import CONFIDENCE_THRESHOLD
from shared.schemas import (
    CitizenProfile,
    EligibilityStatus,
    GroundedEligibilityVerdict,
    MatchResult,
    NextBestSchemeRecommendation,
    RejectionExplanation,
    ReviewerAuditResult,
    Scheme,
)

logger = logging.getLogger(__name__)


class LLMMatcher:
    """Evaluates citizen eligibility against schemes using LLM inference with ChromaDB evidence grounding."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        search_engine: Optional[SemanticSearchEngine] = None,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ):
        self.llm = llm_client or LLMClient()
        self.search_engine = search_engine or SemanticSearchEngine()
        self.confidence_threshold = confidence_threshold

    def evaluate_scheme_grounded(
        self, profile: CitizenProfile, scheme: Scheme
    ) -> GroundedEligibilityVerdict:
        """Evaluates citizen facts against a specific scheme's official policy document.
        Requires verbatim evidence quotes and applies two-pass Reviewer verification.
        """
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Retrieve official source text from ChromaDB
        evidence_rec = self.search_engine.get_scheme_evidence(scheme.id)
        if evidence_rec and evidence_rec.get("document"):
            source_text = evidence_rec["document"]
        else:
            # Fallback to official scheme definition text if vector collection is not yet populated
            crit_text = "\n".join(f"- {c.description}" for c in scheme.criteria)
            docs_text = ", ".join(scheme.documents_required)
            source_text = (
                f"Scheme Name: {scheme.name}\n"
                f"Ministry: {scheme.ministry}\n"
                f"Official URL: {scheme.official_url}\n"
                f"Benefits: {scheme.benefits}\n"
                f"Description: {scheme.description}\n"
                f"Official Eligibility Criteria:\n{crit_text}\n"
                f"Documents Required:\n{docs_text}\n"
            )

        known_facts = profile.known_fields()
        facts_json = json.loads(mask_aadhaar(json.dumps(known_facts, default=str)))
        facts_str = json.dumps(facts_json, ensure_ascii=False, indent=2)

        prompt = f"""You are YojanaAgent's Senior Government Policy Evaluator.
The current date is {today_str}.

Analyze the citizen's profile facts against the following official government scheme text:

=== OFFICIAL SCHEME TEXT ===
{source_text}
============================

=== CITIZEN PROFILE FACTS ===
{facts_str}
=============================

Evaluation Rules:
1. Status must be one of:
   - 'ELIGIBLE' (citizen meets all mandatory criteria established in the official text)
   - 'ALMOST' (citizen meets known criteria, but some essential facts are missing/unknown)
   - 'NOT_ELIGIBLE' (citizen violates at least one strict criterion)
2. GROUNDING REQUIREMENT: You MUST include verbatim quotes from the official scheme text in 'evidence_quotes' supporting your determination.
3. Show your date/age calculations in 'date_calculation_reasoning' relative to {today_str}.
4. Provide a clear, citizen-facing explanation in 'explanation'.
5. List 'satisfied_reasons', 'missing_fields', and 'disqualifying_reasons'.
6. Assign a confidence score between 0.0 and 1.0 reflecting your certainty.
"""

        # Primary LLM evaluation pass
        verdict: Optional[GroundedEligibilityVerdict] = None
        for attempt in range(2):
            try:
                inst, llm_res = self.llm.generate_structured(
                    prompt=prompt,
                    schema_class=GroundedEligibilityVerdict,
                    system_prompt="You are a strict, evidence-grounded government scheme eligibility examiner.",
                )
                if inst:
                    verdict = inst
                    verdict.scheme_id = scheme.id
                    verdict.scheme_name = scheme.name
                    verdict.benefit_summary = scheme.benefits
                    verdict.documents_required = scheme.documents_required

                    # Verify evidence_quotes are present
                    if not verdict.evidence_quotes and attempt == 0:
                        logger.warning("Eligibility verdict missing evidence quotes on attempt 1. Retrying.")
                        prompt += "\n\nCRITICAL: Your previous response omitted 'evidence_quotes'. You MUST extract exact verbatim sentences from the source text into 'evidence_quotes'."
                        continue
                    break
            except Exception as e:
                logger.error("LLM eligibility evaluation attempt %d failed: %s", attempt, e)

        if not verdict:
            # Safe conservative assessment if LLM fails or is unavailable
            return GroundedEligibilityVerdict(
                scheme_id=scheme.id,
                scheme_name=scheme.name,
                status="NEEDS_REVIEW",
                confidence=0.0,
                evidence_quotes=[],
                satisfied_reasons=[],
                missing_fields=profile.unknown_fields(),
                disqualifying_reasons=["LLM evaluation unavailable for this scheme."],
                date_calculation_reasoning=f"Evaluated on {today_str}",
                explanation="Automated LLM evaluation is temporarily unavailable.",
                benefit_summary=scheme.benefits,
                documents_required=scheme.documents_required,
                needs_review=True,
                audit_notes="LLM call failed or returned empty result.",
            )

        # 2. Second-pass Reviewer Audit Step
        audit_result = self._review_verdict(verdict, source_text, facts_str, today_str)
        if not audit_result.agrees or verdict.confidence < self.confidence_threshold or audit_result.audit_confidence < self.confidence_threshold:
            verdict.needs_review = True
            verdict.status = "NEEDS_REVIEW"
            verdict.audit_notes = (
                f"Auditor disagreement ({audit_result.reason}) or low confidence "
                f"(evaluator={verdict.confidence:.2f}, auditor={audit_result.audit_confidence:.2f})."
            )
            logger.info("Scheme %s flagged as NEEDS_REVIEW: %s", scheme.id, verdict.audit_notes)

        return verdict

    def _review_verdict(
        self,
        verdict: GroundedEligibilityVerdict,
        source_text: str,
        facts_str: str,
        today_str: str,
    ) -> ReviewerAuditResult:
        """Audits the primary verdict against the official text to detect hallucinations."""
        reviewer_prompt = f"""You are an independent Policy Auditor for government benefits.
The current date is {today_str}.

Audit the following proposed eligibility determination:
Proposed Status: {verdict.status}
Confidence: {verdict.confidence}
Evidence Quotes: {verdict.evidence_quotes}
Disqualifying Reasons: {verdict.disqualifying_reasons}
Satisfied Reasons: {verdict.satisfied_reasons}

Source Policy Document:
{source_text}

Citizen Profile Facts:
{facts_str}

Check:
1. Do the evidence quotes actually appear verbatim in the source text?
2. Does the proposed status logically follow from the citizen facts and official rules?
3. Set agrees=true if the determination is strictly supported; agrees=false if flawed or hallucinated.
"""
        try:
            audit, _ = self.llm.generate_structured(
                prompt=reviewer_prompt,
                schema_class=ReviewerAuditResult,
                system_prompt="You are an uncompromising policy reviewer verifying official facts.",
            )
            if audit:
                return audit
        except Exception as e:
            logger.warning("Reviewer audit failed: %s", e)

        return ReviewerAuditResult(agrees=True, audit_confidence=verdict.confidence, reason="Audit check bypassed")

    def evaluate_all_grounded(
        self, profile: CitizenProfile, schemes: list[Scheme]
    ) -> list[GroundedEligibilityVerdict]:
        """Evaluates a citizen profile across candidate schemes."""
        verdicts: list[GroundedEligibilityVerdict] = []
        for scheme in schemes:
            v = self.evaluate_scheme_grounded(profile, scheme)
            verdicts.append(v)
        return verdicts

    def explain_rejection(
        self, verdict: GroundedEligibilityVerdict, language: str = "en"
    ) -> RejectionExplanation:
        """Generates an empathetic, grounded explanation of disqualification with next steps."""
        prompt = f"""You are an empathetic, citizen-first advisor for YojanaAgent.
Formulate a compassionate, clear, plain-language explanation of why the citizen is currently not eligible (or missing requirements) for scheme '{verdict.scheme_name}'.

Determined Status: {verdict.status}
Disqualifying Reasons: {verdict.disqualifying_reasons}
Missing Requirements: {verdict.missing_fields}
Source Evidence: {verdict.evidence_quotes}
Language: {language} (If 'hi', write in gentle, clear Hindi; if 'en', write in supportive English).

Instructions:
1. Explain the specific reason respectfully without bureaucratic jargon.
2. Provide actionable next steps (e.g., getting a certificate, visiting CSC, updating land records).
3. Mention potential alternative programs if applicable.
4. Return structured output matching RejectionExplanation.
"""
        try:
            explanation, _ = self.llm.generate_structured(
                prompt=prompt,
                schema_class=RejectionExplanation,
                system_prompt="You explain government eligibility decisions with clarity and empathy.",
            )
            if explanation:
                explanation.scheme_id = verdict.scheme_id
                explanation.scheme_name = verdict.scheme_name
                return explanation
        except Exception as err:
            logger.warning("LLM explain_rejection failed: %s. Using safe template.", err)

        # Fallback explanation
        reason_txt = "; ".join(verdict.disqualifying_reasons) or "Mandatory eligibility criteria not met."
        if language == "hi":
            plain = f"वर्तमान में आप {verdict.scheme_name} के लिए पात्र नहीं हैं। कारण: {reason_txt}"
            steps = ["निकटतम सीएससी केंद्र पर जाकर दस्तावेजों की पुष्टि करें", "वैकल्पिक योजनाओं की जांच करें"]
        else:
            plain = f"You do not currently meet the eligibility requirements for {verdict.scheme_name}. Reason: {reason_txt}"
            steps = ["Verify details with your local CSC center", "Explore alternative government schemes"]

        return RejectionExplanation(
            scheme_id=verdict.scheme_id,
            scheme_name=verdict.scheme_name,
            plain_language_reason=plain,
            blocking_criteria=verdict.disqualifying_reasons,
            evidence_quote=verdict.evidence_quotes[0] if verdict.evidence_quotes else "",
            suggested_next_steps=steps,
            alternative_schemes=[],
        )

    def recommend_next_best(
        self, profile: CitizenProfile, ineligible_scheme_id: str, top_k: int = 3
    ) -> list[NextBestSchemeRecommendation]:
        """Finds closest alternative schemes using semantic search and citizen context."""
        all_schemes = {s.id: s for s in load_all_schemes()}
        ref_scheme = all_schemes.get(ineligible_scheme_id)
        query = ref_scheme.category_tags[0] if ref_scheme and ref_scheme.category_tags else "government assistance"

        search_results = self.search_engine.search(query=query, top_k=top_k + 2)
        recommendations: list[NextBestSchemeRecommendation] = []

        for res in search_results:
            if res.scheme_id == ineligible_scheme_id:
                continue
            scheme_obj = all_schemes.get(res.scheme_id)
            if not scheme_obj:
                continue

            recommendations.append(
                NextBestSchemeRecommendation(
                    scheme_id=res.scheme_id,
                    scheme_name=res.name,
                    match_reason=f"Matches category related to {res.metadata.get('category_tags', 'citizen support')}",
                    benefit_summary=scheme_obj.benefits,
                    confidence=res.score,
                )
            )
            if len(recommendations) >= top_k:
                break

        return recommendations
