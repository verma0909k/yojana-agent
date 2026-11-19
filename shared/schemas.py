"""Shared schemas for YojanaAgent.
Frozen after initial specification to keep contracts solid across modules.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar, Union
from pydantic import BaseModel, Field

T = TypeVar("T")


# --- 1. Confidence & Provenance ---

class Source(str, Enum):
    USER_TEXT = "user_text"
    USER_VOICE = "user_voice"
    DOCUMENT = "document"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class Fact(BaseModel, Generic[T]):
    """Atomic fact with value, confidence score (0.0 to 1.0), and provenance."""
    value: Optional[T] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: Source = Source.UNKNOWN

    @property
    def known(self) -> bool:
        return self.value is not None


# --- 2. Demographic Enums ---

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Category(str, Enum):
    GENERAL = "general"
    OBC = "obc"
    SC = "sc"
    ST = "st"
    EWS = "ews"


class Occupation(str, Enum):
    FARMER = "farmer"
    STUDENT = "student"
    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    LABOURER = "labourer"
    HOMEMAKER = "homemaker"
    UNEMPLOYED = "unemployed"
    RETIRED = "retired"


class EducationLevel(str, Enum):
    CLASS_10 = "class_10"
    CLASS_12 = "class_12"
    DIPLOMA = "diploma"
    GRADUATE = "graduate"
    TECHNICAL_DEGREE = "technical_degree"
    POSTGRADUATE = "postgraduate"


# --- 3. Citizen Profile ---

class CitizenProfile(BaseModel):
    """Structured citizen profile with field-level confidence and provenance."""
    age: Fact[int] = Fact()
    gender: Fact[Gender] = Fact()
    state: Fact[str] = Fact()
    district: Fact[str] = Fact()
    is_rural: Fact[bool] = Fact()
    annual_income: Fact[int] = Fact()          # rupees per year
    category: Fact[Category] = Fact()
    occupation: Fact[Occupation] = Fact()
    land_holding_acres: Fact[float] = Fact()
    education_level: Fact[str] = Fact()        # e.g. "class_10", "class_12", "graduate", "technical_degree"
    is_disabled: Fact[bool] = Fact()
    is_bpl: Fact[bool] = Fact()
    family_size: Fact[int] = Fact()
    has_bank_account: Fact[bool] = Fact()
    has_aadhaar: Fact[bool] = Fact()
    works_in_fisheries: Fact[bool] = Fact()
    is_shg_member: Fact[bool] = Fact()

    def known_fields(self) -> dict[str, Any]:
        return {k: v.value for k, v in self if isinstance(v, Fact) and v.known}

    def unknown_fields(self) -> list[str]:
        return [k for k, v in self if isinstance(v, Fact) and not v.known]

    def low_confidence_fields(self, threshold: float = 0.7) -> list[str]:
        return [k for k, v in self if isinstance(v, Fact) and v.known and v.confidence < threshold]

    def set_fact(self, field_name: str, value: Any, confidence: float = 1.0, source: Source = Source.USER_TEXT):
        """Helper to update a fact by field name."""
        if hasattr(self, field_name):
            setattr(self, field_name, Fact(value=value, confidence=confidence, source=source))


# --- 4. Rule Engine & Scheme Schemas ---

class CriterionOperator(str, Enum):
    EQ = "eq"              # field == val
    NEQ = "neq"            # field != val
    GTE = "gte"            # field >= val
    LTE = "lte"            # field <= val
    IN = "in"              # field in val
    NOT_IN = "not_in"      # field not in val
    IS_TRUE = "is_true"    # field is True
    IS_FALSE = "is_false"  # field is False


class Criterion(BaseModel):
    """Deterministic eligibility rule condition, supports atomic and compound OR logic."""
    field: str
    operator: CriterionOperator
    value: Optional[Any] = None
    description: str                       # e.g. "Age must be at least 18"
    disqualification_reason: str           # e.g. "Applicant is younger than 18 years"
    or_conditions: list[Criterion] = Field(default_factory=list)  # Alternative conditions that also satisfy this criterion


class Scheme(BaseModel):
    """Complete official government scheme definition."""
    id: str
    name: str
    name_hi: Optional[str] = None
    ministry: str
    description: str
    benefits: str
    official_url: str
    category_tags: list[str] = Field(default_factory=list)
    criteria: list[Criterion] = Field(default_factory=list)
    documents_required: list[str] = Field(default_factory=list)
    is_active: bool = True
    deadline: Optional[str] = None


class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    ALMOST = "ALMOST"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


class MatchResult(BaseModel):
    """Outcome of rule-engine evaluation on a single scheme."""
    scheme_id: str
    scheme_name: str
    status: EligibilityStatus
    satisfied_reasons: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    disqualifying_reasons: list[str] = Field(default_factory=list)
    deciding_rule: Optional[str] = None
    benefit_summary: str = ""
    official_url: str = ""
    documents_required: list[str] = Field(default_factory=list)
    deadline: Optional[str] = None


# --- 5. Trace & Orchestrator State ---

class AgentActionType(str, Enum):
    EXTRACT_CITIZEN_PROFILE = "extract_citizen_profile"
    SEARCH_SCHEMES = "search_schemes"
    GET_SCHEME_DETAILS = "get_scheme_details"
    IDENTIFY_INFORMATION_GAPS = "identify_information_gaps"
    ASK_CITIZEN_QUESTION = "ask_citizen_question"
    COMPARE_ELIGIBILITY = "compare_eligibility"
    VERIFY_OFFICIAL_SOURCE = "verify_official_source"
    PREPARE_APPLICATION = "prepare_application"
    FINALIZE = "finalize"


class EligibilityConfidence(str, Enum):
    LIKELY_ELIGIBLE = "LIKELY_ELIGIBLE"
    POSSIBLY_ELIGIBLE = "POSSIBLY_ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    NEEDS_OFFICIAL_VERIFICATION = "NEEDS_OFFICIAL_VERIFICATION"


class EvidenceGrounding(BaseModel):
    """Verifiable source claim extracted directly from an official scheme source."""
    claim: str
    source_url: str
    source_quote: Optional[str] = None
    verified_at: Optional[str] = None
    confidence: float = 1.0
    status: str = "verified"                # "verified", "unverified", "needs_verification"


class PlanDecision(BaseModel):
    """Structured planning decision formulated by the LLM Brain."""
    citizen_goal: str
    current_understanding: str
    information_gaps: list[str] = Field(default_factory=list)
    proposed_action: AgentActionType = AgentActionType.SEARCH_SCHEMES
    selected_tool: str = "search_schemes"
    tool_args: dict[str, Any] = Field(default_factory=dict)
    expected_outcome: str = ""
    reason: str = ""
    requires_replanning: bool = False
    requires_approval: bool = False
    is_terminal: bool = False


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionResult(BaseModel):
    tool_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TraceStep(BaseModel):
    """Single step log entry for the live agent trace panel."""
    agent_name: str                        # "Planner", "Asker", "Matcher", "Verifier", "Critic"
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None


class AgentState(BaseModel):
    """State passing through the LangGraph loop."""
    session_id: str = "default_session"
    profile: CitizenProfile = Field(default_factory=CitizenProfile)
    user_query: str = ""
    language: str = "en"
    candidate_schemes: list[str] = Field(default_factory=list)
    match_results: list[MatchResult] = Field(default_factory=list)
    pending_questions: list[str] = Field(default_factory=list)
    asked_fields: list[str] = Field(default_factory=list)
    portal_checks: dict[str, dict] = Field(default_factory=dict)
    verified_schemes: list[str] = Field(default_factory=list)
    critic_notes: list[str] = Field(default_factory=list)
    trace_steps: list[TraceStep] = Field(default_factory=list)
    step_count: int = 0
    max_steps: int = 8
    next_node: str = "planner"
    is_complete: bool = False
    is_paused: bool = False
    pause_reason: str = ""
    final_response: str = ""
    current_goal: str = ""
    plan_decision: Optional[PlanDecision] = None
    plan_history: list[PlanDecision] = Field(default_factory=list)
    evidence_records: list[EvidenceGrounding] = Field(default_factory=list)
    execution_context: dict[str, Any] = Field(default_factory=dict)


# --- 6. Phase 1 Document Vault & Consistency Schemas ---

class FieldConfidence(BaseModel):
    field_name: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    value_str: Optional[str] = None


class DocumentExtraction(BaseModel):
    """Structured extraction returned by multimodal vision LLM from citizen identity/revenue documents."""
    doc_type: str = Field(description="Detected document type (e.g., Aadhaar Card, Income Certificate, Caste Certificate, Ration Card, Land Record, Bank Passbook)")
    holder_name: Optional[str] = Field(default=None, description="Full name of certificate holder or citizen")
    date_of_birth: Optional[str] = Field(default=None, description="Date of birth in YYYY-MM-DD or DD/MM/YYYY format if present")
    issue_date: Optional[str] = Field(default=None, description="Document issue date in YYYY-MM-DD if printed")
    expiry_date: Optional[str] = Field(default=None, description="Explicit expiration date if printed on document")
    validity_period: Optional[str] = Field(default=None, description="Validity period textual clause if printed (e.g., 'Valid for 1 year from date of issue')")
    income_amount: Optional[int] = Field(default=None, description="Annual or monthly family income figure in Rupees if stated")
    id_last4: Optional[str] = Field(default=None, description="Last 4 digits of document ID/Aadhaar/Passbook number (masked for privacy)")
    per_field_confidence: list[FieldConfidence] = Field(default_factory=list, description="Confidence score per extracted field")
    raw_summary: Optional[str] = Field(default="", description="Brief extracted summary of document body")


class ConsistencyIssue(BaseModel):
    """Identified inconsistency across multiple citizen documents or against stated profile facts."""
    id: str = Field(description="Unique issue identifier")
    severity: str = Field(default="medium", description="'high', 'medium', or 'low'")
    message: str = Field(description="Plain-language description of mismatch")
    documents: list[str] = Field(default_factory=list, description="Document filenames or types involved in the conflict")
    field_name: str = Field(default="", description="Field with conflicting values (e.g. holder_name, date_of_birth, annual_income)")
    evidence: str = Field(default="", description="Verbatim quote or evidence string showing conflict")


class DocumentConsistencyReport(BaseModel):
    """Overall consistency audit report across all citizen documents and profile facts."""
    issues: list[ConsistencyIssue] = Field(default_factory=list)
    is_consistent: bool = True
    checked_at: Optional[str] = None


class StoredDocumentMetadata(BaseModel):
    """Metadata record for an encrypted document stored inside data/vault/<user_id>/."""
    doc_id: str
    user_id: str
    filename: str
    doc_type: str
    holder_name: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    income_amount: Optional[int] = None
    id_last4: Optional[str] = None
    linked_scheme_ids: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    created_at: str
    file_path: str
    mime_type: str = "image/jpeg"


# --- 7. Phase 2 Document Validity & Expiry Schemas ---

class ReviewerAuditResult(BaseModel):
    """Auditing verdict returned by second-pass Reviewer LLM."""
    agrees: bool = Field(description="Whether the Reviewer agrees with the primary verdict")
    reason: str = Field(description="Detailed evidentiary reason for agreement or disagreement")
    audit_confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class DocumentValidityVerdict(BaseModel):
    """LLM decision regarding document validity, days remaining, and renewal actions."""
    doc_id: str
    doc_type: str
    status: str = Field(description="'VALID', 'EXPIRING_SOON', 'EXPIRED', or 'NEEDS_REVIEW'")
    expiry_date: Optional[str] = Field(default=None, description="Computed or printed expiration date (YYYY-MM-DD)")
    days_remaining: Optional[int] = Field(default=None, description="Days between current injected date and expiry_date")
    date_calculation_reasoning: str = Field(description="Explicit date arithmetic explaining days remaining relative to today")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    needs_review: bool = False
    review_reason: Optional[str] = None
    affected_applications: list[str] = Field(default_factory=list, description="Applications blocked or impacted by this document")
    renewal_steps: list[str] = Field(default_factory=list, description="Step-by-step renewal instructions for the citizen")
    nearest_office_guidance: Optional[str] = Field(default="Nearest Tehsil Revenue Office or CSC Center")
    regulatory_disclaimer: str = "We detect expiry and guide renewal steps, but you must renew the document yourself with the issuing revenue authority."


class DocumentHealthSummary(BaseModel):
    """Overall document health summary with circular score metrics and renewal urgency list."""
    user_id: str
    total_documents: int
    valid_count: int
    expiring_soon_count: int
    expired_count: int
    health_percent: int
    verdicts: list[DocumentValidityVerdict] = Field(default_factory=list)
    generated_at: str
    disclaimer: str = "The system detects expiry and provides renewal guidance, but cannot renew documents on your behalf."


# --- 8. Phase 3 Scheme Policy Changes & Extracted Deadlines ---

class SchemeChangeSummary(BaseModel):
    """AI-detected policy change between official portal snapshot and current gazette."""
    id: str = Field(description="Unique change event identifier")
    scheme_id: str = Field(description="Scheme identifier affected (e.g. nsp-scholarship, pm-kisan)")
    summary: str = Field(description="Plain-language description of policy update (e.g. 'Income ceiling raised to ₹3.0 Lakh')")
    before: str = Field(description="Previous policy requirement or text")
    after: str = Field(description="New updated policy requirement or text")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    detected_on: str = Field(description="Date change was detected (YYYY-MM-DD)")
    status: str = Field(default="NEEDS_REVIEW", description="'NEEDS_REVIEW', 'APPROVED', or 'REJECTED'")
    affects_user: bool = False
    evidence_quotes: list[str] = Field(default_factory=list, description="Verbatim quote copied from official portal text")


class ExtractedDeadline(BaseModel):
    """Application window or milestone date extracted from government portal with evidence quote."""
    id: str = Field(description="Unique deadline identifier")
    scheme_id: str = Field(description="Scheme identifier")
    stage: str = Field(description="Milestone stage (e.g. 'Fresh Applications Close', 'Institute Verification')")
    date_str: str = Field(description="Normalized date string (e.g. '2026-03-31')")
    source_quote: str = Field(description="Verbatim line from portal text as evidence")
    days_remaining: Optional[int] = Field(default=None, description="Days remaining from current date")
    status: str = Field(default="open", description="'open', 'closing_soon', or 'closed'")
    extracted_on: str = Field(description="Date extracted (YYYY-MM-DD)")


class SchemeExtractionBundle(BaseModel):
    """Structured result returned by LLM comparing official portal text with snapshot."""
    changes: list[SchemeChangeSummary] = Field(default_factory=list)
    deadlines: list[ExtractedDeadline] = Field(default_factory=list)
    has_policy_change: bool = False
    audit_notes: str = ""


# --- 9. Phase 4 Notification & Outbound Message Draft Schemas ---

class OutboundMessageDraft(BaseModel):
    """AI-prepared message awaiting explicit citizen approval before dispatch."""
    id: str = Field(description="Unique draft identifier")
    user_id: str = Field(description="Citizen ID this draft was prepared for")
    channel: str = Field(description="'email', 'telegram', 'sms', or 'in_app'")
    recipient: str = Field(description="Email address, Telegram handle/chat_id, or mobile number")
    subject: Optional[str] = Field(default=None, description="Email subject line or notification title")
    body: str = Field(description="Message body text generated in the citizen's preferred language")
    language: str = Field(default="en", description="Language of generated message (e.g. 'en', 'hi')")
    status: str = Field(default="PENDING_APPROVAL", description="'PENDING_APPROVAL', 'APPROVED', 'SENT', or 'DISCARDED'")
    created_at: str = Field(description="ISO timestamp when draft was formulated")
    sent_at: Optional[str] = Field(default=None, description="ISO timestamp when user approved and message was sent")
    approval_guarantee: str = "Nothing is sent without your approval."
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftGenerationRequest(BaseModel):
    """Request payload for the LLM to draft an outbound citizen alert or inquiry."""
    user_id: str
    event_type: str = Field(description="e.g. 'DOCUMENT_EXPIRY', 'DEADLINE_REMINDER', 'TEHSIL_VERIFICATION_INQUIRY', 'CSC_APPOINTMENT'")
    recipient: str
    channel: str = Field(default="email", description="'email', 'telegram', or 'sms'")
    language: str = Field(default="en", description="'en' or 'hi'")
    context_data: dict[str, Any] = Field(default_factory=dict)


class DraftActionResponse(BaseModel):
    """Result of draft approval, sending, or discard action."""
    draft_id: str
    status: str
    dispatched: bool
    channel: str
    message: str


class GeneratedDraftContent(BaseModel):
    """Structured response from LLM for message drafting."""
    subject: Optional[str] = Field(default=None, description="Clear, concise subject line (for email) or header")
    body: str = Field(description="Polite, clear, actionable message body in requested language with masked Aadhaar")
    language: str = Field(default="en", description="Detected or generated language ('en', 'hi')")
    reasoning: str = Field(default="", description="Reasoning behind tone and wording")


# --- 10. Phase 5 LLM Matcher & Profile Conflict Schemas ---

class GroundedEligibilityVerdict(BaseModel):
    """LLM-grounded eligibility assessment for a scheme backed by verbatim source evidence."""
    scheme_id: str
    scheme_name: str
    status: str = Field(description="'ELIGIBLE', 'ALMOST', 'NOT_ELIGIBLE', or 'NEEDS_REVIEW'")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from 0.0 to 1.0")
    evidence_quotes: list[str] = Field(default_factory=list, description="Verbatim quotes copied from official source text")
    satisfied_reasons: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    disqualifying_reasons: list[str] = Field(default_factory=list)
    date_calculation_reasoning: str = Field(default="", description="Calculations for age, dates, or expiry")
    explanation: str = Field(default="", description="Citizen-facing summary of why they qualify or what is missing")
    benefit_summary: str = Field(default="")
    documents_required: list[str] = Field(default_factory=list)
    needs_review: bool = False
    audit_notes: str = ""


class RejectionExplanation(BaseModel):
    """Compassionate, grounded explanation of why a citizen was rejected or almost eligible."""
    scheme_id: str
    scheme_name: str
    plain_language_reason: str = Field(description="Clear explanation in citizen's language")
    blocking_criteria: list[str] = Field(default_factory=list)
    evidence_quote: str = Field(default="", description="Verbatim quote from scheme policy causing rejection")
    suggested_next_steps: list[str] = Field(default_factory=list)
    alternative_schemes: list[str] = Field(default_factory=list)


class ProfileConflictItem(BaseModel):
    """Discrepancy detected between self-reported citizen profile and verified vault documents."""
    field_name: str
    stated_value: str
    document_value: str
    document_source: str
    conflict_severity: str = Field(default="MEDIUM", description="'HIGH', 'MEDIUM', 'LOW'")
    clarification_question_en: str
    clarification_question_hi: str


class NextBestSchemeRecommendation(BaseModel):
    """Alternative scheme recommendation when citizen is ineligible for primary query."""
    scheme_id: str
    scheme_name: str
    match_reason: str
    benefit_summary: str
    confidence: float = 1.0






