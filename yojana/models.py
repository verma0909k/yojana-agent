from __future__ import annotations
from enum import Enum
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class Source(str, Enum):
    USER_TEXT = "user_text"
    USER_VOICE = "user_voice"
    DOCUMENT = "document"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class Fact(BaseModel, Generic[T]):
    """One piece of profile info plus how much we trust it."""
    value: Optional[T] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: Source = Source.UNKNOWN

    @property
    def known(self) -> bool:
        return self.value is not None


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


class CitizenProfile(BaseModel):
    age: Fact[int] = Fact()
    gender: Fact[Gender] = Fact()
    state: Fact[str] = Fact()
    district: Fact[str] = Fact()
    is_rural: Fact[bool] = Fact()
    annual_income: Fact[int] = Fact()          # rupees per year
    category: Fact[Category] = Fact()
    occupation: Fact[Occupation] = Fact()
    land_holding_acres: Fact[float] = Fact()
    education_level: Fact[str] = Fact()        # e.g. "class_12", "graduate"
    is_disabled: Fact[bool] = Fact()
    is_bpl: Fact[bool] = Fact()
    family_size: Fact[int] = Fact()
    has_bank_account: Fact[bool] = Fact()
    has_aadhaar: Fact[bool] = Fact()

    def known_fields(self) -> dict:
        return {k: v.value for k, v in self if v.known}

    def unknown_fields(self) -> list[str]:
        return [k for k, v in self if not v.known]

    def low_confidence_fields(self, threshold: float = 0.7) -> list[str]:
        return [k for k, v in self if v.known and v.confidence < threshold]