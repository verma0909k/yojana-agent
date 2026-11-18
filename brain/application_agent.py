"""Application Execution Agent: Converts scheme recommendations into actionable application packages and tracking tasks."""

from typing import Any, Optional
from pathlib import Path

from experience.actions.pdf_filler import generate_application_pdf
from experience.dashboard.application_tracker import ApplicationTracker
from knowledge.schemes.data import load_all_schemes
from shared.schemas import (
    CitizenProfile,
    EligibilityStatus,
    MatchResult,
    Scheme,
)


class ApplicationAgent:
    """Orchestrates end-to-end scheme application preparation, pre-filling, and lifecycle progression."""

    def __init__(self, tracker: Optional[ApplicationTracker] = None):
        self.tracker = tracker or ApplicationTracker()
        self._schemes_cache: dict[str, Scheme] = {s.id: s for s in load_all_schemes()}

    def get_scheme(self, scheme_id: str) -> Scheme:
        if scheme_id not in self._schemes_cache:
            self._schemes_cache = {s.id: s for s in load_all_schemes()}
        scheme = self._schemes_cache.get(scheme_id)
        if not scheme:
            raise ValueError(f"Scheme ID '{scheme_id}' does not exist.")
        return scheme

    def evaluate_document_readiness(
        self,
        scheme: Scheme,
        available_documents: list[str],
    ) -> dict[str, Any]:
        """Compares citizen's uploaded/declared documents against mandatory scheme requirements."""
        import re
        ready = []
        missing = []

        for req in scheme.documents_required:
            req_clean = req.lower().strip()
            req_tokens = {w for w in re.findall(r"\w+", req_clean) if len(w) > 3}
            matched = False
            for avail in available_documents:
                avail_clean = avail.lower().strip()
                avail_tokens = {w for w in re.findall(r"\w+", avail_clean) if len(w) > 3}
                if avail_clean in req_clean or req_clean in avail_clean:
                    matched = True
                    break
                if req_tokens and len(req_tokens & avail_tokens) >= 1:
                    matched = True
                    break
            if matched:
                ready.append(req)
            else:
                missing.append(req)

        return {
            "required": scheme.documents_required,
            "ready": ready,
            "missing": missing,
            "is_ready": len(missing) == 0,
            "readiness_pct": round((len(ready) / max(len(scheme.documents_required), 1)) * 100, 1),
        }

    def prepare_application_package(
        self,
        scheme_id: str,
        profile: CitizenProfile,
        available_documents: Optional[list[str]] = None,
        citizen_id: str = "active_citizen",
        generate_pdf: bool = True,
    ) -> dict[str, Any]:
        """Generates a complete application package: checklist, pre-filled PDF, submission guidance, and persistent task."""
        scheme = self.get_scheme(scheme_id)
        docs = available_documents or []

        # Auto-detect documents from known profile facts
        if profile.has_aadhaar.known and profile.has_aadhaar.value:
            if "Aadhaar Card" not in docs:
                docs.append("Aadhaar Card")
        if profile.has_bank_account.known and profile.has_bank_account.value:
            if "Bank Account Details" not in docs:
                docs.append("Bank Account Details")

        readiness = self.evaluate_document_readiness(scheme, docs)

        # Pre-fill PDF form if requested
        pdf_path: Optional[str] = None
        if generate_pdf:
            match = MatchResult(
                scheme_id=scheme.id,
                scheme_name=scheme.name,
                status=EligibilityStatus.ELIGIBLE,
                official_url=scheme.official_url,
                documents_required=scheme.documents_required,
                satisfied_reasons=["Application package prepared by YojanaAgent"],
            )
            pdf_path = generate_application_pdf(profile, match)

        status = "READY_TO_SUBMIT" if readiness["is_ready"] else "DRAFT"
        guidance = [
            f"1. Review the generated pre-filled application form: {Path(pdf_path).name if pdf_path else 'Form generated'}.",
            f"2. Ensure all required documents are ready ({len(readiness['ready'])} of {len(readiness['required'])} prepared).",
            f"3. Submit directly at the official portal: {scheme.official_url} or visit your nearest Common Service Centre (CSC).",
        ]
        if readiness["missing"]:
            guidance.insert(
                1,
                f"   [Action Needed] Obtain missing documents: {', '.join(readiness['missing'])}.",
            )

        # Persist task in ApplicationTracker
        task = self.tracker.create_task(
            citizen_id=citizen_id,
            scheme_id=scheme.id,
            scheme_name=scheme.name,
            documents_ready=readiness["ready"],
            documents_missing=readiness["missing"],
            status=status,
            pdf_path=pdf_path,
            official_portal_url=scheme.official_url,
            submission_mode="ONLINE" if scheme.official_url.startswith("https") else "OFFLINE_CSC",
            notes=f"Auto-generated application package. Document readiness: {readiness['readiness_pct']}%",
        )

        return {
            "task_id": task["task_id"],
            "scheme_id": scheme.id,
            "scheme_name": scheme.name,
            "status": status,
            "readiness": readiness,
            "pdf_path": pdf_path,
            "submission_url": scheme.official_url,
            "action_guidance": "\n".join(guidance),
            "task_details": task,
        }

    def update_status(self, task_id: str, new_status: str, notes: str = "") -> dict[str, Any]:
        """Updates lifecycle status of an application task."""
        return self.tracker.update_task_status(task_id, status=new_status, notes=notes)

    def list_citizen_applications(self, citizen_id: str) -> list[dict[str, Any]]:
        """Lists all application tasks for a citizen."""
        return self.tracker.list_tasks(citizen_id=citizen_id)
