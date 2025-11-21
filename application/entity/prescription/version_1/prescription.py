"""
Prescription entity for healthcare application.

Represents a prescription issued by a doctor to a patient with medication
details, dosage, and refill information.
"""

from datetime import datetime, timezone
from typing import ClassVar

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Prescription(CyodaEntity):
    """
    Prescription entity representing a medication prescription.
    
    Contains prescription details including medication, dosage, instructions,
    and refill tracking for patient medication management.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Prescription"
    ENTITY_VERSION: ClassVar[int] = 1

    # Business ID field
    prescription_id: str = Field(..., description="Business identifier for the prescription")

    # Prescription details
    patient_id: str = Field(..., description="ID of the patient")
    doctor_id: str = Field(..., description="ID of the prescribing doctor")
    medication_name: str = Field(..., description="Name of the prescribed medication")
    dosage: str = Field(..., description="Dosage instructions for the medication")
    instructions: str = Field(..., description="Additional instructions for taking the medication")
    issued_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="When the prescription was issued (ISO 8601)"
    )
    refills_remaining: int = Field(..., description="Number of refills remaining")

    @field_validator("patient_id", "doctor_id")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Validate patient and doctor IDs."""
        if not v or len(v.strip()) == 0:
            raise ValueError("ID must be non-empty")
        return v.strip()

    @field_validator("medication_name")
    @classmethod
    def validate_medication_name(cls, v: str) -> str:
        """Validate medication name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Medication name must be non-empty")
        if len(v.strip()) > 200:
            raise ValueError("Medication name must be at most 200 characters long")
        return v.strip()

    @field_validator("dosage")
    @classmethod
    def validate_dosage(cls, v: str) -> str:
        """Validate dosage instructions."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Dosage must be non-empty")
        if len(v.strip()) > 100:
            raise ValueError("Dosage must be at most 100 characters long")
        return v.strip()

    @field_validator("instructions")
    @classmethod
    def validate_instructions(cls, v: str) -> str:
        """Validate medication instructions."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Instructions must be non-empty")
        if len(v.strip()) > 1000:
            raise ValueError("Instructions must be at most 1000 characters long")
        return v.strip()

    @field_validator("issued_at")
    @classmethod
    def validate_issued_at(cls, v: str) -> str:
        """Validate issued datetime."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Issued at must be non-empty")
        
        try:
            # Parse ISO 8601 datetime
            datetime.fromisoformat(v.strip().replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Issued at must be in ISO 8601 format")
        
        return v.strip()

    @field_validator("refills_remaining")
    @classmethod
    def validate_refills_remaining(cls, v: int) -> int:
        """Validate refills remaining count."""
        if v < 0:
            raise ValueError("Refills remaining must be non-negative")
        if v > 12:  # Reasonable upper limit
            raise ValueError("Refills remaining must be at most 12")
        return v

    def has_refills_available(self) -> bool:
        """Check if prescription has refills available."""
        return self.refills_remaining > 0

    def use_refill(self) -> bool:
        """Use one refill if available. Returns True if successful."""
        if self.has_refills_available():
            self.refills_remaining -= 1
            return True
        return False

    def is_recently_issued(self, days: int = 30) -> bool:
        """Check if prescription was issued within the specified number of days."""
        try:
            issued_datetime = datetime.fromisoformat(self.issued_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_diff = (now - issued_datetime).days
            return days_diff <= days
        except ValueError:
            return False

    def get_prescription_age_days(self) -> int:
        """Get the age of the prescription in days."""
        try:
            issued_datetime = datetime.fromisoformat(self.issued_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return (now - issued_datetime).days
        except ValueError:
            return 0

    def is_expired(self, expiry_days: int = 365) -> bool:
        """Check if prescription is expired based on issue date."""
        return self.get_prescription_age_days() > expiry_days

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
