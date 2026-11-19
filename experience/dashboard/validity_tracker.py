"""LLM-driven Document Validity Tracking, Expiry Reasoning, Affected Application Analysis,
and Reviewer Self-Check for YojanaAgent.
"""

from datetime import datetime, timezone
from typing import Optional
from brain.llm_client import LLMClient
from experience.dashboard.application_tracker import ApplicationTracker
from experience.intake.vault import DocumentVault
from shared.schemas import (
    DocumentHealthSummary,
    DocumentValidityVerdict,
    ReviewerAuditResult,
    StoredDocumentMetadata,
)


class ValidityTracker:
    """Evaluates certificate validity and renewal workflows using two-pass LLM reasoning."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        vault: Optional[DocumentVault] = None,
        app_tracker: Optional[ApplicationTracker] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.vault = vault or DocumentVault()
        self.app_tracker = app_tracker or ApplicationTracker()

    def evaluate_document_validity(
        self,
        doc: StoredDocumentMetadata,
        active_apps: list[dict],
        current_date_iso: Optional[str] = None,
    ) -> DocumentValidityVerdict:
        """Evaluates a single document's validity status using LLM reasoning with injected date."""
        today_str = current_date_iso or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        relevant_apps = [
            f"App #{a.get('task_id', '')} for '{a.get('scheme_name', '')}' (status: {a.get('status', '')})"
            for a in active_apps
            if doc.doc_id in str(a.get("documents_ready", []))
            or any(sid in str(a.get("scheme_id", "")) for sid in doc.linked_scheme_ids)
        ]

        prompt = (
            f"TODAY'S DATE: {today_str}\n\n"
            f"Document Details:\n"
            f"- Document ID: {doc.doc_id}\n"
            f"- Document Type: {doc.doc_type}\n"
            f"- Holder Name: {doc.holder_name}\n"
            f"- Issue Date: {doc.issue_date or 'Not stated'}\n"
            f"- Printed Expiry Date: {doc.expiry_date or 'None printed'}\n"
            f"- Linked Schemes: {doc.linked_scheme_ids}\n"
            f"- Citizen's Active Applications: {relevant_apps or 'None currently active'}\n\n"
            f"Statutory Validity Rules in India:\n"
            f"1. Income Certificate: 1 financial year or 365 days from issue date.\n"
            f"2. OBC Non-Creamy Layer / EWS: 1 financial year (expires March 31 of issuing year or 1 year from issue).\n"
            f"3. Caste Certificate (SC/ST): Lifetime validity unless state re-verification required.\n"
            f"4. Land Records (Khasra/Jamabandi): 6 months validity for fresh scheme applications.\n"
            f"5. Aadhaar / PAN / Bank Passbook: Lifetime validity (no expiry) unless biometric update flagged.\n\n"
            f"Instructions:\n"
            f"- Inject TODAY'S DATE ({today_str}) into your calculation.\n"
            f"- Calculate exact days remaining until expiry in the date_calculation_reasoning field.\n"
            f"- Set status to 'EXPIRED' if days_remaining <= 0; 'EXPIRING_SOON' if 0 < days_remaining <= 30; 'VALID' if > 30 days or lifetime.\n"
            f"- List all affected applications blocked if this document is expired or expiring soon.\n"
            f"- Provide 3 concrete step-by-step renewal instructions."
        )

        system_prompt = (
            "You are an expert Indian revenue documentation and administrative validity auditor. "
            "You calculate certificate validity deterministically with strict date arithmetic."
        )

        verdict, res = self.llm.generate_structured(
            prompt=prompt,
            schema_class=DocumentValidityVerdict,
            system_prompt=system_prompt,
        )

        if not verdict or not res.ok:
            # Fallback deterministic math
            verdict = self._deterministic_fallback_verdict(doc, today_str, relevant_apps)

        # Step 2: Reviewer Step (Second LLM call with a different auditor prompt)
        reviewer_audit = self._run_reviewer_audit(doc, verdict, today_str)

        if not reviewer_audit.agrees or reviewer_audit.audit_confidence < 0.7 or verdict.confidence < 0.7:
            verdict.status = "NEEDS_REVIEW"
            verdict.needs_review = True
            verdict.review_reason = (
                f"Reviewer audit flagged discrepancy: {reviewer_audit.reason} "
                f"(Audit confidence: {reviewer_audit.audit_confidence})"
            )

        return verdict

    def _run_reviewer_audit(
        self,
        doc: StoredDocumentMetadata,
        verdict: DocumentValidityVerdict,
        today_str: str,
    ) -> ReviewerAuditResult:
        """Second-pass Reviewer LLM call auditing the primary verdict against statutory rules."""
        audit_prompt = (
            f"AUDIT ASSESSMENT\n"
            f"Today's Date: {today_str}\n"
            f"Document: {doc.doc_type} (Issued: {doc.issue_date}, Printed Expiry: {doc.expiry_date})\n"
            f"Primary Verdict under review:\n"
            f"- Status: {verdict.status}\n"
            f"- Computed Expiry Date: {verdict.expiry_date}\n"
            f"- Days Remaining: {verdict.days_remaining}\n"
            f"- Reasoning: {verdict.date_calculation_reasoning}\n\n"
            f"Audit Task:\n"
            f"Cross-verify the primary verdict's date arithmetic and statutory validity rules. "
            f"Do you agree with this status and calculation? If any arithmetic or statutory error exists, "
            f"set agrees to false and explain why in detail."
        )

        reviewer_system = (
            "You are an independent Senior Verification Reviewer. You strictly audit legal validity verdicts. "
            "If an assessment miscalculated dates or wrongly marked a document, you disagree."
        )

        audit_res, _ = self.llm.generate_structured(
            prompt=audit_prompt,
            schema_class=ReviewerAuditResult,
            system_prompt=reviewer_system,
        )

        if audit_res:
            return audit_res

        # Fallback audit: basic sanity check on days_remaining
        if verdict.days_remaining is not None:
            if verdict.days_remaining <= 0 and verdict.status != "EXPIRED":
                return ReviewerAuditResult(agrees=False, reason="Days remaining <= 0 but status not EXPIRED", audit_confidence=0.9)
            if verdict.days_remaining > 30 and verdict.status == "EXPIRED":
                return ReviewerAuditResult(agrees=False, reason="Days remaining > 30 but status is EXPIRED", audit_confidence=0.9)

        return ReviewerAuditResult(agrees=True, reason="Deterministic sanity checks passed", audit_confidence=0.95)

    def _deterministic_fallback_verdict(
        self,
        doc: StoredDocumentMetadata,
        today_str: str,
        relevant_apps: list[str],
    ) -> DocumentValidityVerdict:
        """Deterministic validity calculation when LLM service is offline."""
        status = "VALID"
        days_left = 365
        expiry = doc.expiry_date
        reasoning = "Lifetime or unexpired certificate"

        try:
            today_dt = datetime.strptime(today_str, "%Y-%m-%d")
            if doc.expiry_date:
                exp_dt = datetime.strptime(doc.expiry_date, "%Y-%m-%d")
                days_left = (exp_dt - today_dt).days
                if days_left <= 0:
                    status = "EXPIRED"
                elif days_left <= 30:
                    status = "EXPIRING_SOON"
                else:
                    status = "VALID"
                reasoning = f"Printed expiry {doc.expiry_date} minus today {today_str} = {days_left} days remaining."
            elif doc.issue_date:
                iss_dt = datetime.strptime(doc.issue_date, "%Y-%m-%d")
                # Default 1-year validity for revenue certificates
                exp_dt = iss_dt.replace(year=iss_dt.year + 1)
                expiry = exp_dt.strftime("%Y-%m-%d")
                days_left = (exp_dt - today_dt).days
                if days_left <= 0:
                    status = "EXPIRED"
                elif days_left <= 30:
                    status = "EXPIRING_SOON"
                else:
                    status = "VALID"
                reasoning = f"Issued on {doc.issue_date}. Standard 1-year validity expires on {expiry}. Days left: {days_left}."
        except Exception as e:
            reasoning = f"Could not parse dates ({e}). Flagged for manual review."
            status = "NEEDS_REVIEW"

        return DocumentValidityVerdict(
            doc_id=doc.doc_id,
            doc_type=doc.doc_type,
            status=status,
            expiry_date=expiry,
            days_remaining=days_left,
            date_calculation_reasoning=reasoning,
            confidence=0.85,
            affected_applications=relevant_apps,
            renewal_steps=[
                "Visit your state e-District or Antyodaya Saral portal.",
                "Submit previous certificate copy and electricity bill proof.",
                "Complete revenue Patwari verification and download renewed digital certificate.",
            ],
            nearest_office_guidance="Nearest Tehsil Revenue Complex or Common Service Centre (CSC)",
        )

    def get_user_health_summary(
        self,
        user_id: str,
        current_date_iso: Optional[str] = None,
    ) -> DocumentHealthSummary:
        """Calculates comprehensive document health summary across all vault documents of user_id."""
        docs = self.vault.list_documents(user_id)
        active_apps = self.app_tracker.list_tasks(citizen_id=user_id)
        today_str = current_date_iso or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        verdicts = [
            self.evaluate_document_validity(d, active_apps, current_date_iso=today_str)
            for d in docs
        ]

        # Sort by urgency: EXPIRED first, then EXPIRING_SOON, then NEEDS_REVIEW, then VALID
        urgency_order = {"EXPIRED": 1, "EXPIRING_SOON": 2, "NEEDS_REVIEW": 3, "VALID": 4}
        verdicts.sort(key=lambda v: urgency_order.get(v.status, 5))

        total = len(verdicts)
        valid_cnt = sum(1 for v in verdicts if v.status == "VALID")
        expiring_cnt = sum(1 for v in verdicts if v.status == "EXPIRING_SOON")
        expired_cnt = sum(1 for v in verdicts if v.status == "EXPIRED")
        health_pct = round((valid_cnt / total) * 100) if total > 0 else 100

        now_iso = datetime.now(timezone.utc).isoformat()
        return DocumentHealthSummary(
            user_id=user_id,
            total_documents=total,
            valid_count=valid_cnt,
            expiring_soon_count=expiring_cnt,
            expired_count=expired_cnt,
            health_percent=health_pct,
            verdicts=verdicts,
            generated_at=now_iso,
        )
