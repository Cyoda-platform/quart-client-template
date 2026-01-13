from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Applicant(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Applicant"
    ENTITY_VERSION: ClassVar[int] = 1

    first_name: str = Field(..., description="First name of applicant")
    last_name: str = Field(..., description="Last name of applicant")
    email: str = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    date_of_birth: str = Field(..., description="Date of birth (ISO 8601)")
    ssn_last_four: str = Field(..., description="Last 4 digits of SSN")

    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State/Province")
    zip_code: str = Field(..., description="Postal code")
    country: str = Field(default="US", description="Country code")

    annual_income: float = Field(..., description="Annual income in USD")
    employment_status: str = Field(
        ..., description="EMPLOYED, SELF_EMPLOYED, UNEMPLOYED, RETIRED"
    )
    employment_years: int = Field(..., description="Years at current employment")

    loan_amount: float = Field(..., description="Requested loan amount")
    loan_purpose: str = Field(..., description="PERSONAL, AUTO, HOME, BUSINESS")
    loan_term_months: int = Field(..., description="Requested loan term in months")

    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when applicant was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when applicant was last updated",
    )

    enrichment_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="enrichmentData",
        description="Data from enrichment pipeline (geolocation, device risk, identity verification)",
    )

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @field_validator("annual_income")
    @classmethod
    def validate_income(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Annual income must be non-negative")
        return v

    @field_validator("loan_amount")
    @classmethod
    def validate_loan_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Loan amount must be positive")
        return v
