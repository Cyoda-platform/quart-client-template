# entity/customer/version_1/customer.py

"""
Customer entity for Cyoda Client Application

Represents a customer with basic contact information including
id, name, email, and phone fields.
"""

import re
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Customer(CyodaEntity):
    """
    Customer represents a customer entity with basic contact information.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> active -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Customer"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields
    customer_id: str = Field(..., description="Business identifier for the customer")
    name: str = Field(..., description="Full name of the customer")
    email: str = Field(..., description="Email address of the customer")
    phone: str = Field(..., description="Phone number of the customer")

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

        # Basic email validation pattern
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
                "Phone must contain only digits and common separators (spaces, dashes, parentheses, plus)"
            )

        if len(cleaned_phone) < 10:
            raise ValueError("Phone must be at least 10 digits long")
        if len(cleaned_phone) > 15:
            raise ValueError("Phone must be at most 15 digits long")

        return v.strip()

    def get_display_name(self) -> str:
        """Get display name for the customer"""
        return f"{self.name} ({self.customer_id})"

    def get_contact_info(self) -> str:
        """Get formatted contact information"""
        return f"Email: {self.email}, Phone: {self.phone}"

    def is_active_customer(self) -> bool:
        """Check if customer is in active state"""
        return self.state == "active"
