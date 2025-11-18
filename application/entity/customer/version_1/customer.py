# entity/customer/version_1/customer.py

"""
Customer Entity for Cyoda Client Application

Represents a customer in the system with comprehensive customer management
functionality including contact information, address, and status tracking.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, EmailStr, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Customer(CyodaEntity):
    """
    Customer entity represents a customer in the system with contact information,
    address details, and status tracking.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> validated -> active -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Customer"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required customer fields
    name: str = Field(..., description="Full name of the customer")
    email: EmailStr = Field(..., description="Email address of the customer")
    phone: str = Field(..., description="Phone number of the customer")

    # Address information
    address_line1: str = Field(
        ..., description="Primary address line", alias="addressLine1"
    )
    address_line2: Optional[str] = Field(
        default=None, description="Secondary address line", alias="addressLine2"
    )
    city: str = Field(..., description="City")
    state: Optional[str] = Field(default=None, description="State or province")
    postal_code: str = Field(..., description="Postal or ZIP code", alias="postalCode")
    country: str = Field(..., description="Country")

    # Customer status and preferences
    is_active: Optional[bool] = Field(
        default=True,
        alias="isActive",
        description="Flag indicating if the customer is active",
    )
    customer_type: str = Field(
        default="INDIVIDUAL",
        alias="customerType",
        description="Type of customer (INDIVIDUAL, BUSINESS, PREMIUM)",
    )

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
    validation_result: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="validationResult",
        description="Result of customer validation checks",
    )
    enriched_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="enrichedData",
        description="Additional data populated during processing",
    )

    # Validation rules
    ALLOWED_CUSTOMER_TYPES: ClassVar[List[str]] = [
        "INDIVIDUAL",
        "BUSINESS",
        "PREMIUM",
        "CORPORATE",
    ]

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate customer name field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Customer name must be non-empty")
        if len(v) < 2:
            raise ValueError("Customer name must be at least 2 characters long")
        if len(v) > 100:
            raise ValueError("Customer name must be at most 100 characters long")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Phone number must be non-empty")
        # Basic phone validation - remove spaces and check length
        phone_clean = (
            v.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        )
        if len(phone_clean) < 10:
            raise ValueError("Phone number must be at least 10 digits")
        if len(phone_clean) > 15:
            raise ValueError("Phone number must be at most 15 digits")
        return v.strip()

    @field_validator("customer_type")
    @classmethod
    def validate_customer_type(cls, v: str) -> str:
        """Validate customer type field"""
        if v not in cls.ALLOWED_CUSTOMER_TYPES:
            raise ValueError(
                f"Customer type must be one of: {cls.ALLOWED_CUSTOMER_TYPES}"
            )
        return v

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        """Validate postal code field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Postal code must be non-empty")
        if len(v) > 20:
            raise ValueError("Postal code must be at most 20 characters long")
        return v.strip()

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Customer":
        """Validate business logic rules"""
        customer_type = self.customer_type
        is_active = self.is_active

        # Business logic validation
        if customer_type not in self.ALLOWED_CUSTOMER_TYPES:
            raise ValueError(
                f"Customer type must be one of: {self.ALLOWED_CUSTOMER_TYPES}"
            )

        if customer_type == "PREMIUM" and is_active is False:
            raise ValueError("PREMIUM customers must be active")

        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def set_validation_result(self, validation_result: Dict[str, Any]) -> None:
        """Set validation result and update timestamp"""
        self.validation_result = validation_result
        self.update_timestamp()

    def set_enriched_data(self, enriched_data: Dict[str, Any]) -> None:
        """Set enriched data and update timestamp"""
        self.enriched_data = enriched_data
        self.update_timestamp()

    def is_ready_for_activation(self) -> bool:
        """Check if customer is ready for activation (in validated state)"""
        return self.state == "validated"

    def is_activated(self) -> bool:
        """Check if customer has been activated"""
        return self.state == "active" or self.state == "completed"

    def get_full_address(self) -> str:
        """Get formatted full address"""
        address_parts = [self.address_line1]
        if self.address_line2:
            address_parts.append(self.address_line2)
        address_parts.extend([self.city, self.postal_code, self.country])
        if self.state:
            address_parts.insert(-2, self.state)
        return ", ".join(address_parts)

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
