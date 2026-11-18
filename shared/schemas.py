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
    final_response: str = ""
    current_goal: str = ""
    plan_decision: Optional[PlanDecision] = None
    plan_history: list[PlanDecision] = Field(default_factory=list)
    evidence_records: list[EvidenceGrounding] = Field(default_factory=list)
    execution_context: dict[str, Any] = Field(default_factory=dict)
