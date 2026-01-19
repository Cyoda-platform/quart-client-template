"""
Policy entity for insurance policies in claims platform.

Represents insurance policies with coverage details and validation.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Policy(CyodaEntity):
    """
    Policy represents an insurance policy with coverage and validity details.
    
    Used for claim validation and coverage checks.
    """

    ENTITY_NAME: ClassVar[str] = "Policy"
    ENTITY_VERSION: ClassVar[int] = 1

    policy_number: str = Field(..., description="Unique policy number")
    policyholder_id: str = Field(..., description="ID of policyholder")
    policy_type: str = Field(..., description="Type (AUTO, HOME, LIFE, HEALTH)")
    coverage_amount: float = Field(..., description="Total coverage amount")
    deductible: float = Field(..., description="Deductible amount")
    effective_date: str = Field(..., description="Policy effective date (ISO 8601)")
    expiration_date: str = Field(..., description="Policy expiration date (ISO 8601)")
    is_active: bool = Field(default=True, description="Whether policy is active")
    coverage_details: Dict[str, Any] = Field(
        default_factory=dict, description="Coverage details"
    )

    @field_validator("policy_type")
    @classmethod
    def validate_policy_type(cls, v: str) -> str:
        allowed = ["AUTO", "HOME", "LIFE", "HEALTH"]
        if v not in allowed:
            raise ValueError(f"Policy type must be one of {allowed}")
        return v

    @field_validator("coverage_amount", "deductible")
    @classmethod
    def validate_amounts(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v

    def is_valid_for_claim(self, claim_date: str) -> bool:
        """Check if policy is valid for a claim date"""
        return (
            self.is_active
            and self.effective_date <= claim_date <= self.expiration_date
        )

