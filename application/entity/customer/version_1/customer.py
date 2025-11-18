# entity/customer/version_1/customer.py

"""
Customer entity for Cyoda Client Application

Represents a customer with basic contact information including
id, name, email, and phone fields as requested.
"""

import re
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Customer(CyodaEntity):
    """
    Customer entity represents a customer with basic contact information.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states:
    initial_state -> created -> validated -> processed -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Customer"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields as requested
    customer_id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Customer email address")
    phone: str = Field(..., description="Customer phone number")

    # Optional fields for enhanced functionality
    is_active: Optional[bool] = Field(
        default=True,
        alias="isActive",
        description="Flag indicating if the customer is active",
    )

    # Timestamps (inherited created_at from CyodaEntity,
    # but need to override updated_at behavior)
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the customer was created (ISO 8601)",
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

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Customer ID must be non-empty")
        if len(v) < 3:
            raise ValueError("Customer ID must be at least 3 characters long")
        if len(v) > 50:
            raise ValueError("Customer ID must be at most 50 characters long")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v) > 100:
            raise ValueError("Name must be at most 100 characters long")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")

        # Basic email validation using regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v.strip()):
            raise ValueError("Email must be a valid email address")

        if len(v) > 255:
            raise ValueError("Email must be at most 255 characters long")
        return v.strip().lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Phone must be non-empty")

        # Remove common phone number separators for validation
        cleaned_phone = re.sub(r"[\s\-\(\)\+\.]", "", v.strip())

        # Check if it contains only digits after cleaning
        if not cleaned_phone.isdigit():
            raise ValueError(
                "Phone must contain only digits and common separators "
                "(spaces, dashes, parentheses, plus)"
            )

        if len(cleaned_phone) < 10:
            raise ValueError("Phone must be at least 10 digits long")
        if len(cleaned_phone) > 15:
            raise ValueError("Phone must be at most 15 digits long")

        return v.strip()

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
