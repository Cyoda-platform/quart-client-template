# entity/customer/version_1/customer.py

"""
Customer entity for Cyoda Client Application

Represents a customer with basic contact information and address details.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Customer(CyodaEntity):
    """
    Customer entity represents a customer with contact information.
    
    Inherits from CyodaEntity to get common fields like entity_id, created_at, 
    updated_at, state, etc.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Customer"
    ENTITY_VERSION: ClassVar[int] = 1

    # Customer-specific fields
    name: str = Field(..., description="Customer full name")
    email: str = Field(..., description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer phone number")
    address: Optional[str] = Field(None, description="Customer address")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field"""
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
        """Validate email field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")
        
        # Basic email validation
        email = v.strip().lower()
        if "@" not in email or "." not in email:
            raise ValueError("Email must be a valid email address")
        
        if len(email) > 254:
            raise ValueError("Email must be at most 254 characters long")
        
        return email

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone field"""
        if v is None:
            return v
        
        phone = v.strip()
        if len(phone) == 0:
            return None
        
        if len(phone) > 20:
            raise ValueError("Phone must be at most 20 characters long")
        
        return phone

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate address field"""
        if v is None:
            return v
        
        address = v.strip()
        if len(address) == 0:
            return None
        
        if len(address) > 500:
            raise ValueError("Address must be at most 500 characters long")
        
        return address

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
