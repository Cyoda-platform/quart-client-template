# entity/customer/version_1/customer.py

"""
Customer Entity for Cyoda Client Application

Represents a customer with comprehensive contact information and address details.
Includes validation for email uniqueness and required fields as specified in requirements.
"""

import re
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Address(BaseModel):
    """Address information for a customer"""

    street: Optional[str] = Field(default=None, description="Street address")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State or province")
    zip: Optional[str] = Field(default=None, description="ZIP or postal code")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )


class Customer(CyodaEntity):
    """
    Customer entity representing a customer with contact information and address.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> validated -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Customer"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Customer email address (unique)")

    # Optional fields
    phone: Optional[str] = Field(default=None, description="Customer phone number")
    address: Optional[Address] = Field(default=None, description="Customer address")

    # Timestamps (auto-managed)
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Timestamp when the customer was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        description="Timestamp when the customer was last updated (ISO 8601 format)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field according to requirements"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name is required and must be non-empty")
        if len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v.strip()) > 100:
            raise ValueError("Name must be at most 100 characters long")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email field according to requirements"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email is required and must be non-empty")

        # Basic email format validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v.strip()):
            raise ValueError("Email must be a valid email address")

        if len(v.strip()) > 255:
            raise ValueError("Email must be at most 255 characters long")

        return v.strip().lower()  # Normalize email to lowercase

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone field if provided"""
        if v is None:
            return v

        if len(v.strip()) == 0:
            return None  # Empty string becomes None

        # Basic phone validation - allow various formats
        phone_clean = re.sub(r"[^\d+\-\(\)\s]", "", v.strip())
        if len(phone_clean) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        if len(phone_clean) > 20:
            raise ValueError("Phone number must be at most 20 characters")

        return v.strip()

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Customer":
        """Validate business logic rules"""
        # Additional business validation can be added here
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
