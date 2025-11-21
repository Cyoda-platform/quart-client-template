"""
Appointment entity for healthcare application.

Represents an appointment between a patient and a doctor with scheduling
and status information.
"""

from datetime import datetime
from typing import ClassVar, List

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Appointment(CyodaEntity):
    """
    Appointment entity representing a scheduled appointment between a patient and doctor.
    
    Manages appointment scheduling, status tracking, and reason for visit.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Appointment"
    ENTITY_VERSION: ClassVar[int] = 1

    # Business ID field
    appointment_id: str = Field(..., description="Business identifier for the appointment")

    # Appointment details
    patient_id: str = Field(..., description="ID of the patient")
    doctor_id: str = Field(..., description="ID of the doctor")
    scheduled_at: str = Field(..., description="Scheduled appointment datetime (ISO 8601)")
    status: str = Field(..., description="Appointment status")
    reason: str = Field(..., description="Reason for the appointment")

    # Valid appointment statuses
    VALID_STATUSES: ClassVar[List[str]] = [
        "requested",
        "confirmed", 
        "cancelled",
        "completed"
    ]

    @field_validator("patient_id", "doctor_id")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Validate patient and doctor IDs."""
        if not v or len(v.strip()) == 0:
            raise ValueError("ID must be non-empty")
        return v.strip()

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, v: str) -> str:
        """Validate scheduled datetime and ensure it's in the future."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Scheduled datetime must be non-empty")
        
        try:
            # Parse ISO 8601 datetime
            scheduled_datetime = datetime.fromisoformat(v.strip().replace('Z', '+00:00'))
            
            # Check if it's in the future
            if scheduled_datetime <= datetime.now(scheduled_datetime.tzinfo):
                raise ValueError("Scheduled datetime must be in the future")
                
        except ValueError as e:
            if "Invalid isoformat string" in str(e) or "time data" in str(e):
                raise ValueError("Scheduled datetime must be in ISO 8601 format")
            raise
        
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate appointment status."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Status must be non-empty")
        
        status_lower = v.strip().lower()
        if status_lower not in cls.VALID_STATUSES:
            raise ValueError(f"Status must be one of: {cls.VALID_STATUSES}")
        
        return status_lower

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        """Validate appointment reason."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Reason must be non-empty")
        if len(v.strip()) > 500:
            raise ValueError("Reason must be at most 500 characters long")
        return v.strip()

    def is_upcoming(self) -> bool:
        """Check if appointment is upcoming (scheduled in the future)."""
        try:
            scheduled_datetime = datetime.fromisoformat(self.scheduled_at.replace('Z', '+00:00'))
            return scheduled_datetime > datetime.now(scheduled_datetime.tzinfo)
        except ValueError:
            return False

    def can_be_cancelled(self) -> bool:
        """Check if appointment can be cancelled."""
        return self.status in ["requested", "confirmed"] and self.is_upcoming()

    def can_be_completed(self) -> bool:
        """Check if appointment can be marked as completed."""
        return self.status == "confirmed"

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
