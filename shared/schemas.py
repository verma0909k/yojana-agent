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
    education_level: Fact[str] = Fact()        # e.g. "class_10", "class_12", "graduate"
    is_disabled: Fact[bool] = Fact()
    is_bpl: Fact[bool] = Fact()
    family_size: Fact[int] = Fact()
    has_bank_account: Fact[bool] = Fact()
    has_aadhaar: Fact[bool] = Fact()

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
    """Deterministic eligibility rule condition."""
    field: str
    operator: CriterionOperator
    value: Optional[Any] = None
    description: str                       # e.g. "Age must be at least 18"
    disqualification_reason: str           # e.g. "Applicant is younger than 18 years"


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


# --- 5. Trace & Orchestrator State ---

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
    verified_schemes: list[str] = Field(default_factory=list)
    critic_notes: list[str] = Field(default_factory=list)
    trace_steps: list[TraceStep] = Field(default_factory=list)
    step_count: int = 0
    max_steps: int = 8
    next_node: str = "planner"
    is_complete: bool = False
    final_response: str = ""
