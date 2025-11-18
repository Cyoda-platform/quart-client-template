# entity/customer/version_1/customer.py

"""
Customer entity for Cyoda Client Application

Represents a customer business object with basic contact information.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Customer(CyodaEntity):
    """
    Customer represents a customer business object with basic contact information.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Customer"
    ENTITY_VERSION: ClassVar[int] = 1

    # Business identifier field (as requested - "id" maps to customer_id)
    customer_id: str = Field(..., description="Business identifier for the customer")
    
    # Required fields as requested
    name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer phone number")

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer_id field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Customer ID must be non-empty")
        if len(v) > 50:
            raise ValueError("Customer ID must be at most 50 characters long")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        if len(v) > 100:
            raise ValueError("Name must be at most 100 characters long")
        return v.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")
        if "@" not in v:
            raise ValueError("Email must contain @ symbol")
        if len(v) > 255:
            raise ValueError("Email must be at most 255 characters long")
        return v.strip().lower()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone field"""
        if v is None:
            return v
        if len(v.strip()) == 0:
            return None
        if len(v) > 20:
            raise ValueError("Phone must be at most 20 characters long")
        return v.strip()

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
