"""LLM-driven document extraction, scheme document linkage, and cross-document/profile consistency auditing.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from brain.llm_client import LLMClient
from shared.schemas import (
    CitizenProfile,
    ConsistencyIssue,
    DocumentConsistencyReport,
    DocumentExtraction,
    Scheme,
    StoredDocumentMetadata,
)


class LinkedSchemesResult(BaseModel):
    """List of scheme IDs that require this document."""
    matched_scheme_ids: list[str] = Field(
        default_factory=list,
        description="List of scheme IDs whose documents_required matches this document type",
    )
    matching_reason: str = Field(default="", description="Reasoning for linking this document to schemes")


class DocumentExtractor:
    """Orchestrates LLM vision parsing, scheme linkage, and evidentiary consistency auditing."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    def extract_from_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        filename: str = "",
    ) -> DocumentExtraction:
        """Extracts structured DocumentExtraction from document photo using vision LLM."""
        prompt = (
            f"You are an Indian government revenue document verification expert. "
            f"Analyze this document (filename: '{filename}'). Identify document type, holder name, "
            f"date of birth, issue date, expiry date or validity period, income amount if printed, "
            f"and mask any 12-digit Aadhaar to the last 4 digits only. Provide confidence scores for each."
        )

        extraction, res = self.llm.generate_vision_structured(
            image_bytes=image_bytes,
            mime_type=mime_type,
            prompt=prompt,
            schema_class=DocumentExtraction,
        )

        if not extraction or not res.ok:
            # Fallback heuristic placeholder if vision LLM is unconfigured
            doc_type = "Identity Document"
            fn_lower = filename.lower()
            if "aadhaar" in fn_lower or "aadhar" in fn_lower:
                doc_type = "Aadhaar Card"
            elif "income" in fn_lower or "aay" in fn_lower:
                doc_type = "Income Certificate"
            elif "caste" in fn_lower or "obc" in fn_lower or "sc" in fn_lower:
                doc_type = "Caste Certificate"
            elif "ration" in fn_lower:
                doc_type = "Ration Card"

            return DocumentExtraction(
                doc_type=doc_type,
                holder_name="Citizen",
                raw_summary=f"Parsed from {filename}",
            )

        return extraction

    def link_document_to_schemes(
        self,
        extraction: DocumentExtraction,
        schemes: list[Scheme],
    ) -> list[str]:
        """Uses LLM to evaluate which schemes require this document type based on each scheme's documents_required."""
        if not schemes:
            return []

        # Prepare compact scheme documents list
        catalog = [
            {"id": s.id, "name": s.name, "documents_required": s.documents_required}
            for s in schemes
        ]

        prompt = (
            f"Document Extracted Details:\n"
            f"- Document Type: {extraction.doc_type}\n"
            f"- Holder Name: {extraction.holder_name}\n\n"
            f"Available Schemes and their Required Documents:\n"
            f"{catalog}\n\n"
            f"Identify all scheme IDs where '{extraction.doc_type}' satisfies one of their required documents. "
            f"For example, an 'Aadhaar Card' satisfies 'Aadhaar Card' or 'Identity Proof'. "
            f"An 'Income Certificate' satisfies 'Income Certificate' or 'Income Proof'. "
            f"A 'Land Ownership Records / Khasra-Khatauni' satisfies 'Land Record' or 'Khasra-Khatauni'."
        )

        result, _ = self.llm.generate_structured(
            prompt=prompt,
            schema_class=LinkedSchemesResult,
            system_prompt="You are a government scheme documentation auditor. Link uploaded documents to scheme requirements.",
        )

        if result and result.matched_scheme_ids:
            return result.matched_scheme_ids

        # Deterministic keyword fallback
        linked = []
        doc_lower = extraction.doc_type.lower()
        for s in schemes:
            for req in s.documents_required:
                req_lower = req.lower()
                if (
                    doc_lower in req_lower
                    or req_lower in doc_lower
                    or ("aadhaar" in doc_lower and "aadhaar" in req_lower)
                    or ("income" in doc_lower and "income" in req_lower)
                    or ("caste" in doc_lower and "caste" in req_lower)
                    or ("land" in doc_lower and ("land" in req_lower or "khasra" in req_lower))
                ):
                    linked.append(s.id)
                    break
        return linked

    def audit_consistency(
        self,
        documents: list[StoredDocumentMetadata],
        profile: Optional[CitizenProfile] = None,
        schemes: Optional[list[Scheme]] = None,
    ) -> DocumentConsistencyReport:
        """Audits consistency across all uploaded documents and against the citizen's profile facts.
        Detects conflicting names, DOBs, and income figures vs scheme limits with grounded evidence.
        """
        now_str = datetime.now(timezone.utc).isoformat()

        if len(documents) < 2 and (not profile or not profile.known_fields()):
            return DocumentConsistencyReport(issues=[], is_consistent=True, checked_at=now_str)

        docs_summary = [
            {
                "doc_id": d.doc_id,
                "filename": d.filename,
                "doc_type": d.doc_type,
                "holder_name": d.holder_name,
                "issue_date": d.issue_date,
                "expiry_date": d.expiry_date,
                "income_amount": d.income_amount,
                "id_last4": d.id_last4,
            }
            for d in documents
        ]

        profile_summary = profile.known_fields() if profile else {}

        scheme_limits = []
        if schemes:
            for s in schemes:
                income_crit = [c for c in s.criteria if c.field == "annual_income"]
                if income_crit:
                    scheme_limits.append({
                        "scheme_id": s.id,
                        "scheme_name": s.name,
                        "income_threshold": income_crit[0].value,
                    })

        prompt = (
            f"Citizen Profile Facts: {profile_summary}\n\n"
            f"Uploaded Documents in Vault: {docs_summary}\n\n"
            f"Applicable Scheme Eligibility Limits: {scheme_limits}\n\n"
            f"Perform a thorough evidentiary consistency check:\n"
            f"1. Check for name spelling discrepancies across documents and profile (e.g. 'Ananya Verma' vs 'Ananya V').\n"
            f"2. Check if printed income on certificates contradicts stated annual_income or exceeds any scheme's ceiling.\n"
            f"3. Check for conflicting dates of birth or issue/expiry discrepancies.\n"
            f"For every mismatch, construct a ConsistencyIssue with high/medium/low severity and quote the exact conflicting values as evidence."
        )

        report, _ = self.llm.generate_structured(
            prompt=prompt,
            schema_class=DocumentConsistencyReport,
            system_prompt="You are a government fraud-prevention and evidentiary consistency auditor. Detect mismatches across citizen certificates.",
        )

        if report:
            report.checked_at = now_str
            report.is_consistent = len(report.issues) == 0
            return report

        # Deterministic fallback check for names and income if LLM unavailable
        issues: list[ConsistencyIssue] = []
        names = set(d.holder_name for d in documents if d.holder_name)
        if len(names) > 1:
            issues.append(
                ConsistencyIssue(
                    id="issue_name_mismatch",
                    severity="high",
                    message=f"Name spelling differs across uploaded documents: {', '.join(names)}",
                    documents=[d.filename for d in documents if d.holder_name],
                    field_name="holder_name",
                    evidence=f"Different names found: {list(names)}",
                )
            )

        if profile and profile.annual_income.known:
            stated_inc = profile.annual_income.value
            for d in documents:
                if d.income_amount and abs(d.income_amount - stated_inc) > 50000:
                    issues.append(
                        ConsistencyIssue(
                            id=f"issue_income_{d.doc_id}",
                            severity="medium",
                            message=f"Income on {d.filename} (₹{d.income_amount:,}) differs from stated profile income (₹{stated_inc:,}).",
                            documents=[d.filename],
                            field_name="annual_income",
                            evidence=f"Certificate stated ₹{d.income_amount} vs Self-reported ₹{stated_inc}",
                        )
                    )

        return DocumentConsistencyReport(
            issues=issues,
            is_consistent=len(issues) == 0,
            checked_at=now_str,
        )
