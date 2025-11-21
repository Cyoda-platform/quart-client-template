# entity/customer/version_1/customer.py

"""
Customer Entity for Cyoda Client Application

Represents a customer business object with comprehensive validation
for email format, required fields, and business rules.
"""

import re
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Customer(CyodaEntity):
    """
    Customer entity represents a customer business object with
    comprehensive validation and business rules.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> validated -> processed -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Customer"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Customer email address (unique)")
    phone: Optional[str] = Field(default=None, description="Customer phone number")
    address: Optional[str] = Field(default=None, description="Customer address")

    # Timestamps (inherited created_at from CyodaEntity, but need to override updated_at behavior)
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the customer was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the customer was last updated (ISO 8601 format)",
    )

    # Processing-related fields (populated during processing)
    processed_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="processedData",
        description="Data that gets populated during processing",
    )
    validation_result: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="validationResult",
        description="Result of validation checks",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field according to business requirements"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        if len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v) > 100:
            raise ValueError("Name must be at most 100 characters long")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email field with format validation"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")

        # Email format validation using regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v.strip()):
            raise ValueError("Email must be a valid email address")

        if len(v) > 255:
            raise ValueError("Email must be at most 255 characters long")

        return v.strip().lower()  # Normalize to lowercase

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone field if provided"""
        if v is None:
            return v

        if len(v.strip()) == 0:
            return None  # Empty string becomes None

        # Basic phone validation - allow digits, spaces, hyphens, parentheses, plus
        phone_pattern = r"^[\d\s\-\(\)\+\.]+$"
        if not re.match(phone_pattern, v.strip()):
            raise ValueError(
                "Phone must contain only digits, spaces, hyphens, parentheses, and plus signs"
            )

        if len(v) > 20:
            raise ValueError("Phone must be at most 20 characters long")

        return v.strip()

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate address field if provided"""
        if v is None:
            return v

        if len(v.strip()) == 0:
            return None  # Empty string becomes None

        if len(v) > 500:
            raise ValueError("Address must be at most 500 characters long")

        return v.strip()

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Customer":
        """Validate business logic rules"""
        # Basic business validation - ensure required fields are present
        if not self.name or not self.email:
            raise ValueError("Name and email are required fields")

        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def set_processed_data(self, processed_data: Dict[str, Any]) -> None:
        """Set processed data and update timestamp"""
        self.processed_data = processed_data
        self.update_timestamp()

    def set_validation_result(self, validation_result: Dict[str, Any]) -> None:
        """Set validation result and update timestamp"""
        self.validation_result = validation_result
        self.update_timestamp()

    def is_ready_for_processing(self) -> bool:
        """Check if customer is ready for processing (in validated state)"""
        return self.state == "validated"

    def is_processed(self) -> bool:
        """Check if customer has been processed"""
        return self.state == "processed" or self.state == "completed"

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
