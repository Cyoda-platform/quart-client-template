# entity/customer/version_1/customer.py

"""
Customer entity for Cyoda Client Application

Represents a customer with basic contact information including
id, name, email, and phone fields.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Customer(CyodaEntity):
    """
    Customer entity represents a customer with basic contact information.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: none -> created -> validated -> processed -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Customer"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields
    customer_id: str = Field(..., description="Business identifier for the customer")
    name: str = Field(..., description="Full name of the customer")
    email: str = Field(..., description="Email address of the customer")
    phone: str = Field(..., description="Phone number of the customer")

    # Optional fields
    is_active: Optional[bool] = Field(
        default=True,
        alias="isActive",
        description="Flag indicating if the customer is active",
    )

    # Timestamps
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
        
        email = v.strip().lower()
        
        # Basic email validation
        if "@" not in email:
            raise ValueError("Email must contain @ symbol")
        
        parts = email.split("@")
        if len(parts) != 2:
            raise ValueError("Email must have exactly one @ symbol")
        
        local, domain = parts
        if not local or not domain:
            raise ValueError("Email must have both local and domain parts")
        
        if "." not in domain:
            raise ValueError("Email domain must contain at least one dot")
        
        if len(email) > 254:
            raise ValueError("Email must be at most 254 characters long")
        
        return email

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Phone must be non-empty")
        
        phone = v.strip()
        
        # Remove common phone formatting characters
        cleaned_phone = "".join(c for c in phone if c.isdigit() or c in "+()-. ")
        
        if len(cleaned_phone) < 10:
            raise ValueError("Phone must be at least 10 characters long")
        if len(cleaned_phone) > 20:
            raise ValueError("Phone must be at most 20 characters long")
        
        return phone

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
