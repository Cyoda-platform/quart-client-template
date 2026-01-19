"""
Policy entity for insurance policies in claims platform.

Represents insurance policies with coverage details and validation.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Policy(CyodaEntity):
    """
    Policy represents an insurance policy with coverage and validity details.

    Used for claim validation and coverage checks.
    """

    ENTITY_NAME: ClassVar[str] = "Policy"
    ENTITY_VERSION: ClassVar[int] = 1

    policy_number: str = Field(..., alias="policyNumber", description="Unique policy number")
    policyholder_id: str = Field(
        ..., alias="policyholderID", description="ID of policyholder"
    )
    policy_type: str = Field(..., alias="policyType", description="Type of policy")
    coverage_type: str = Field(..., alias="coverageType", description="Coverage type")
    effective_date: str = Field(
        ..., alias="effectiveDate", description="Policy effective date (ISO 8601)"
    )
    expiration_date: str = Field(
        ..., alias="expirationDate", description="Policy expiration date (ISO 8601)"
    )
    premium_amount: float = Field(
        ..., alias="premiumAmount", description="Premium amount"
    )
    deductible: float = Field(..., alias="deductible", description="Deductible amount")
    coverage_limit: float = Field(
        ..., alias="coverageLimit", description="Coverage limit"
    )
    status: str = Field(default="ACTIVE", alias="status", description="Policy status")
    vehicle_vin: Optional[str] = Field(
        default=None, alias="vehicleVIN", description="Vehicle VIN"
    )
    vehicle_make: Optional[str] = Field(
        default=None, alias="vehicleMake", description="Vehicle make"
    )
    vehicle_model: Optional[str] = Field(
        default=None, alias="vehicleModel", description="Vehicle model"
    )
    vehicle_year: Optional[int] = Field(
        default=None, alias="vehicleYear", description="Vehicle year"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the policy was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the policy was last updated (ISO 8601 format)",
    )

    @field_validator("policy_type")
    @classmethod
    def validate_policy_type(cls, v: str) -> str:
        allowed = ["AUTO", "HOME", "LIFE", "HEALTH"]
        if v not in allowed:
            raise ValueError(f"Policy type must be one of {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ["ACTIVE", "INACTIVE", "EXPIRED", "CANCELLED"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    @field_validator("premium_amount", "deductible", "coverage_limit")
    @classmethod
    def validate_amounts(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Policy":
        """Validate business logic rules"""
        if self.premium_amount < 0 or self.deductible < 0 or self.coverage_limit < 0:
            raise ValueError("Amounts must be non-negative")
        return self

    def is_valid_for_claim(self, claim_date: str) -> bool:
        """Check if policy is valid for a claim date"""
        return (
            self.status == "ACTIVE"
            and self.effective_date <= claim_date <= self.expiration_date
        )

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

