"""FastAPI REST API for YojanaAgent.

Provides endpoints for:
- Document Vault (multimodal upload, list, health summary, consistency audit)
- Scheme Intelligence (detected updates, policy deadlines, grounded rejection explanations)
- Human-in-the-Loop Notifications (drafts listing, approval, discard)
- LangGraph scheme evaluation loop
- Right-to-Erasure compliance (DELETE /me/data)

All user-scoped endpoints require or default the X-User-Id header.
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel

from brain.graph import build_graph
from brain.llm_client import mask_aadhaar
from experience.actions.notifier import NotificationService
from experience.dashboard.validity_tracker import ValidityTracker
from experience.intake.doc_extractor import DocumentExtractor
from experience.intake.vault import DocumentVault
from knowledge.llm_matcher import LLMMatcher
from knowledge.monitor import MemoryStore
from knowledge.schemes.data import load_all_schemes
from shared.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from shared.schemas import (
    AgentState,
    CitizenProfile,
    DocumentConsistencyReport,
    DocumentHealthSummary,
    DraftActionResponse,
    MatchResult,
    OutboundMessageDraft,
    RejectionExplanation,
    StoredDocumentMetadata,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="YojanaAgent API",
    version="2.0.0",
    description="LLM-first autonomous government welfare scheme-matching assistant.",
)

# Graph instance for agent matching loop
graph = build_graph()


# --- Dependencies ---

def get_current_user_id(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> str:
    """Extracts and sanitizes the active citizen identifier from X-User-Id header."""
    if x_user_id and x_user_id.strip():
        return "".join(c for c in x_user_id.strip() if c.isalnum() or c in ("-", "_"))
    return "default_citizen"


# --- Request/Response Models ---

class MatchRequest(BaseModel):
    profile: CitizenProfile
    user_query: str = ""
    language: str = "en"


class SendOtpRequest(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None


class SendOtpResponse(BaseModel):
    success: bool
    message: str
    session_id: str
    destination: str


class VerifyOtpRequest(BaseModel):
    code: str
    email: Optional[str] = None
    phone: Optional[str] = None


class VerifyOtpResponse(BaseModel):
    success: bool
    token: str
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None


# Active OTP cache: destination (email or phone) -> {"code": str, "expires_at": float}
_ACTIVE_OTPS: dict[str, dict[str, Any]] = {}


def send_email_otp(to_email: str, otp: str) -> bool:
    """Dispatches a 6-digit OTP code to the citizen's Gmail / email address."""
    subject = f"{otp} is your YojanaAgent verification code"
    body = (
        f"Namaste,\n\n"
        f"Your verification code for YojanaAgent is: {otp}\n\n"
        f"This code will expire in 5 minutes. Do not share this OTP with anyone.\n\n"
        f"Warm regards,\n"
        f"YojanaAgent Team"
    )

    logger.info("==================================================")
    logger.info("[GMAIL OTP DISPATCH] Sent OTP '%s' to: %s", otp, to_email)
    logger.info("==================================================")
    print(f"\n[GMAIL OTP DISPATCH] >>> OTP: {otp} sent to Gmail: {to_email} <<<\n")

    if SMTP_USER and SMTP_PASSWORD:
        try:
            import email.message
            import smtplib

            msg = email.message.EmailMessage()
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM or SMTP_USER
            msg["To"] = to_email
            msg.set_content(body)

            host = SMTP_HOST or "smtp.gmail.com"
            port = SMTP_PORT or 587
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("Live Gmail delivery successful to %s", to_email)
            return True
        except Exception as e:
            logger.warning("SMTP live delivery failed (%s). Fallback logged to console.", e)
            return False
    return True


class ErasureResponse(BaseModel):
    status: str
    user_id: str
    message: str


# --- Authentication & OTP Endpoints ---

@app.post("/auth/send-otp", response_model=SendOtpResponse, tags=["Auth"])
def send_otp(req: SendOtpRequest):
    """Generates and dispatches a 6-digit OTP code to the citizen's Gmail / email or mobile number."""
    otp = f"{random.randint(100000, 999999)}"

    # 1. Prioritize Gmail / Email delivery
    if req.email and req.email.strip():
        clean_email = req.email.strip().lower()
        if "@" not in clean_email:
            raise HTTPException(status_code=400, detail="Invalid email address.")

        _ACTIVE_OTPS[clean_email] = {
            "code": otp,
            "expires_at": time.time() + 300,  # 5 minutes validity
        }

        send_email_otp(clean_email, otp)

        return SendOtpResponse(
            success=True,
            message=f"6-digit verification code sent to your Gmail ({clean_email})",
            session_id=str(uuid.uuid4())[:8],
            destination=clean_email,
        )

    # 2. Fallback to mobile phone
    if req.phone and req.phone.strip():
        clean_digits = "".join(c for c in req.phone if c.isdigit())
        if len(clean_digits) < 10:
            raise HTTPException(status_code=400, detail="Invalid phone number: minimum 10 digits required.")

        _ACTIVE_OTPS[clean_digits] = {
            "code": otp,
            "expires_at": time.time() + 300,
        }

        logger.info("[SMS GATEWAY DISPATCH] Sent OTP '%s' to mobile: %s", otp, req.phone)
        print(f"\n[SMS GATEWAY DISPATCH] >>> OTP: {otp} sent to mobile: {req.phone} <<<\n")

        return SendOtpResponse(
            success=True,
            message=f"6-digit verification code dispatched to mobile ending in {clean_digits[-4:]}",
            session_id=str(uuid.uuid4())[:8],
            destination=req.phone,
        )

    raise HTTPException(status_code=400, detail="Either Gmail/Email or Mobile Number must be provided.")


@app.post("/auth/verify-otp", response_model=VerifyOtpResponse, tags=["Auth"])
def verify_otp(req: VerifyOtpRequest):
    """Verifies the 6-digit code against active generated OTP or standard test code 123456."""
    destination = ""
    user_id = ""

    if req.email and req.email.strip():
        destination = req.email.strip().lower()
        clean_name = "".join(c for c in destination.split("@")[0] if c.isalnum() or c == "_")
        user_id = f"usr_e_{clean_name}"
    elif req.phone and req.phone.strip():
        destination = "".join(c for c in req.phone if c.isdigit())
        user_id = f"usr_p_{destination}"
    else:
        raise HTTPException(status_code=400, detail="Either Gmail/Email or Phone must be provided.")

    cached = _ACTIVE_OTPS.get(destination)

    is_valid = False
    if req.code == "123456":
        is_valid = True
    elif cached and cached["code"] == req.code and time.time() <= cached["expires_at"]:
        is_valid = True
        _ACTIVE_OTPS.pop(destination, None)

    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code.")

    token = f"tok_{uuid.uuid4().hex[:16]}"

    return VerifyOtpResponse(
        success=True,
        token=token,
        user_id=user_id,
        email=req.email,
        phone=req.phone or "",
    )


# --- System & Core Endpoints ---

@app.get("/", tags=["Health"])
def health_check():
    """System health and operational status."""
    return {
        "status": "ok",
        "service": "YojanaAgent API",
        "decision_mode": "llm",
        "regulatory_disclaimer": "The system detects expiry and matches benefits, but cannot renew documents on your behalf.",
    }


@app.post("/match", tags=["Matching"])
def match_schemes(request: MatchRequest, user_id: str = Depends(get_current_user_id)):
    """Executes the complete YojanaAgent LangGraph loop for scheme matching."""
    try:
        initial_state = AgentState(
            profile=request.profile,
            user_query=request.user_query,
            language=request.language,
        )
        final_state = graph.invoke(initial_state)

        # Persist profile and matches to memory store
        store = MemoryStore()
        store.save_profile(user_id, request.profile)
        if final_state.get("match_results"):
            store.save_matches(user_id, final_state["match_results"])

        return {
            "status": "success",
            "user_id": user_id,
            "eligible_schemes": [
                m.model_dump() for m in final_state.get("match_results", []) if m.status == "ELIGIBLE"
            ],
            "almost_schemes": [
                m.model_dump() for m in final_state.get("match_results", []) if m.status == "ALMOST"
            ],
            "trace_steps": [t.model_dump() for t in final_state.get("trace_steps", [])],
            "final_response": final_state.get("final_response", ""),
        }
    except Exception as e:
        logger.error("Match error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# --- Vault Endpoints ---

@app.post("/vault/upload", response_model=StoredDocumentMetadata, tags=["Vault"])
def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """Uploads, Fernet-encrypts, performs multimodal OCR extraction, and stores a citizen document."""
    try:
        if hasattr(file, "file") and hasattr(file.file, "read"):
            file_bytes = file.file.read()
        elif hasattr(file, "read"):
            file_bytes = file.read()
        else:
            file_bytes = b""

        mime_type = getattr(file, "content_type", None) or "image/jpeg"
        filename = getattr(file, "filename", None) or "uploaded_doc.jpg"
        uid = user_id if isinstance(user_id, str) else "default_citizen"

        extractor = DocumentExtractor()
        vault = DocumentVault()
        all_schemes = load_all_schemes()

        # Extract structured fields and link to schemes
        extraction = extractor.extract_from_image(file_bytes, mime_type=mime_type)
        linked_schemes = extractor.link_document_to_schemes(extraction, schemes=all_schemes)

        # Encrypt and store under data/vault/<user_id>/
        metadata = vault.save_document(
            user_id=uid,
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
            extraction=extraction,
            linked_scheme_ids=linked_schemes,
        )
        return metadata
    except Exception as e:
        logger.error("Upload error for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Document upload and extraction failed: {e}")


@app.get("/vault/documents", response_model=list[StoredDocumentMetadata], tags=["Vault"])
def list_documents(user_id: str = Depends(get_current_user_id)):
    """Lists all encrypted vault documents belonging to the authenticated citizen."""
    vault = DocumentVault()
    uid = user_id if isinstance(user_id, str) else "default_citizen"
    return vault.list_documents(user_id=uid)


@app.get("/vault/health", response_model=DocumentHealthSummary, tags=["Vault"])
def get_vault_health(user_id: str = Depends(get_current_user_id)):
    """Evaluates document validity, expiring items, and renewal steps with required legal disclaimer."""
    tracker = ValidityTracker()
    uid = user_id if isinstance(user_id, str) else "default_citizen"
    return tracker.get_user_health_summary(user_id=uid)


@app.get("/vault/consistency", response_model=DocumentConsistencyReport, tags=["Vault"])
def audit_consistency(user_id: str = Depends(get_current_user_id)):
    """Audits consistency across all uploaded vault documents and against the citizen's profile."""
    uid = user_id if isinstance(user_id, str) else "default_citizen"
    store = MemoryStore()
    profile = store.get_profile(uid) or CitizenProfile()
    vault = DocumentVault()
    docs = vault.list_documents(user_id=uid)
    extractor = DocumentExtractor()
    return extractor.audit_consistency(documents=docs, profile=profile)


# --- Schemes, Updates & Deadlines Endpoints ---

@app.get("/schemes/updates", tags=["Schemes"])
def list_scheme_updates(status: Optional[str] = Query(None, description="'NEEDS_REVIEW' or 'APPROVED'")):
    """Returns detected official scheme modifications and diff summaries."""
    store = MemoryStore()
    status_val = status if isinstance(status, str) else None
    return store.get_scheme_updates(status=status_val)


@app.get("/schemes/deadlines", tags=["Schemes"])
def list_upcoming_deadlines():
    """Lists extracted application deadlines and cut-off windows backed by source quotes."""
    store = MemoryStore()
    return store.get_deadlines()


@app.get("/schemes/{scheme_id}/explain-rejection", response_model=RejectionExplanation, tags=["Schemes"])
def explain_scheme_rejection(
    scheme_id: str,
    language: str = Query("en", description="'en' or 'hi'"),
    user_id: str = Depends(get_current_user_id),
):
    """Provides a compassionate, plain-language explanation of why a citizen does not qualify for a scheme."""
    all_schemes = {s.id: s for s in load_all_schemes()}
    scheme = all_schemes.get(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found.")

    uid = user_id if isinstance(user_id, str) else "default_citizen"
    store = MemoryStore()
    profile = store.get_profile(uid) or CitizenProfile()

    matcher = LLMMatcher()
    verdict = matcher.evaluate_scheme_grounded(profile, scheme)
    lang_val = language if isinstance(language, str) else "en"
    explanation = matcher.explain_rejection(verdict, language=lang_val)
    return explanation


# --- Notifications & Outbound Drafts Endpoints ---

@app.get("/drafts", response_model=list[OutboundMessageDraft], tags=["Notifications"])
def list_drafts(
    status: Optional[str] = Query(None, description="'PENDING_APPROVAL', 'SENT', or 'DISCARDED'"),
    user_id: str = Depends(get_current_user_id),
):
    """Lists AI-generated outbound messages awaiting explicit citizen review or history."""
    notifier = NotificationService()
    uid = user_id if isinstance(user_id, str) else "default_citizen"
    status_val = status if isinstance(status, str) else None
    return notifier.list_drafts(user_id=uid, status=status_val)


@app.post("/drafts/{draft_id}/approve", response_model=DraftActionResponse, tags=["Notifications"])
def approve_draft(draft_id: str, user_id: str = Depends(get_current_user_id)):
    """Citizen approval gate: explicitly authorizes dispatch of a pending notification."""
    notifier = NotificationService()
    draft = notifier.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")
    if draft.user_id != user_id and user_id != "default_citizen":
        raise HTTPException(status_code=403, detail="Unauthorized access to message draft.")

    response = notifier.approve_and_send(draft_id)
    return response


@app.post("/drafts/{draft_id}/discard", response_model=DraftActionResponse, tags=["Notifications"])
def discard_draft(draft_id: str, user_id: str = Depends(get_current_user_id)):
    """Citizen rejects and cancels a prepared message draft."""
    notifier = NotificationService()
    draft = notifier.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")
    if draft.user_id != user_id and user_id != "default_citizen":
        raise HTTPException(status_code=403, detail="Unauthorized access to message draft.")

    response = notifier.discard_draft(draft_id)
    return response


# --- Privacy & Right to Erasure Endpoints ---

@app.delete("/me/data", response_model=ErasureResponse, tags=["Privacy"])
def wipe_citizen_data(user_id: str = Depends(get_current_user_id)):
    """Compliance with Right to Erasure: completely purges the citizen's encrypted vault,
    saved profile facts, alerts, match history, and outbound drafts.
    """
    try:
        vault = DocumentVault()
        vault_deleted = vault.delete_user_vault(user_id)

        store = MemoryStore()
        store.delete_citizen_data(user_id)

        msg = (
            f"All personal data and encrypted documents for user '{user_id}' have been permanently erased. "
            f"(Vault deleted: {vault_deleted})"
        )
        logger.info("Right to Erasure invoked for user %s.", user_id)
        return ErasureResponse(status="success", user_id=user_id, message=msg)
    except Exception as e:
        logger.error("Error wiping data for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to erase citizen data: {e}")
