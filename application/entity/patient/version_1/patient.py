"""
Patient entity for healthcare application.

Represents a patient in the healthcare system with personal information,
contact details, and insurance information.
"""

from datetime import datetime
from typing import ClassVar, Optional
import re

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Patient(CyodaEntity):
    """
    Patient entity representing a patient in the healthcare system.
    
    Contains personal information, contact details, and insurance information
    required for healthcare services.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Patient"
    ENTITY_VERSION: ClassVar[int] = 1

    # Business ID field
    patient_id: str = Field(..., description="Business identifier for the patient")

    # Personal information
    first_name: str = Field(..., description="Patient's first name")
    last_name: str = Field(..., description="Patient's last name")
    email: str = Field(..., description="Patient's email address")
    phone: str = Field(..., description="Patient's phone number")
    dob: str = Field(..., description="Patient's date of birth (YYYY-MM-DD)")
    address: str = Field(..., description="Patient's address")
    insurance_provider: str = Field(..., description="Patient's insurance provider")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")
        
        # Basic email validation regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v.strip()):
            raise ValueError("Invalid email format")
        
        return v.strip().lower()

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name fields."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        if len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters long")
        if len(v.strip()) > 50:
            raise ValueError("Name must be at most 50 characters long")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate phone number format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Phone must be non-empty")
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', v)
        if len(digits_only) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        return v.strip()

    @field_validator("dob")
    @classmethod
    def validate_dob(cls, v: str) -> str:
        """Validate date of birth format and ensure it's not in the future."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Date of birth must be non-empty")
        
        try:
            dob_date = datetime.strptime(v.strip(), "%Y-%m-%d")
            if dob_date.date() > datetime.now().date():
                raise ValueError("Date of birth cannot be in the future")
        except ValueError as e:
            if "time data" in str(e):
                raise ValueError("Date of birth must be in YYYY-MM-DD format")
            raise
        
        return v.strip()

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate address field."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Address must be non-empty")
        if len(v.strip()) > 200:
            raise ValueError("Address must be at most 200 characters long")
        return v.strip()

    @field_validator("insurance_provider")
    @classmethod
    def validate_insurance_provider(cls, v: str) -> str:
        """Validate insurance provider field."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Insurance provider must be non-empty")
        if len(v.strip()) > 100:
            raise ValueError("Insurance provider must be at most 100 characters long")
        return v.strip()

    def get_full_name(self) -> str:
        """Get patient's full name."""
        return f"{self.first_name} {self.last_name}"

    def get_age(self) -> int:
        """Calculate patient's age based on date of birth."""
        dob_date = datetime.strptime(self.dob, "%Y-%m-%d").date()
        today = datetime.now().date()
        age = today.year - dob_date.year
        if today.month < dob_date.month or (today.month == dob_date.month and today.day < dob_date.day):
            age -= 1
        return age

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
