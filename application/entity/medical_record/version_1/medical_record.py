"""
MedicalRecord entity for healthcare application.

Represents a medical record containing patient health information with
access control and content management.
"""

from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class MedicalRecord(CyodaEntity):
    """
    MedicalRecord entity representing a patient's medical record.
    
    Contains medical information with access control and content management
    for secure handling of patient health data.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "MedicalRecord"
    ENTITY_VERSION: ClassVar[int] = 1

    # Business ID field
    record_id: str = Field(..., description="Business identifier for the medical record")

    # Medical record details
    patient_id: str = Field(..., description="ID of the patient")
    record_type: str = Field(..., description="Type of medical record")
    content: str = Field(..., description="Medical record content or link to content")
    record_created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="When the medical record was created (ISO 8601)"
    )
    access_level: str = Field(..., description="Access level for the record")

    # Valid record types
    VALID_RECORD_TYPES: ClassVar[List[str]] = [
        "diagnosis",
        "lab_result",
        "prescription",
        "imaging",
        "consultation_note",
        "discharge_summary",
        "vaccination_record",
        "allergy_record",
        "vital_signs",
        "other"
    ]

    # Valid access levels
    VALID_ACCESS_LEVELS: ClassVar[List[str]] = [
        "private",
        "shared"
    ]

    @field_validator("patient_id")
    @classmethod
    def validate_patient_id(cls, v: str) -> str:
        """Validate patient ID."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Patient ID must be non-empty")
        return v.strip()

    @field_validator("record_type")
    @classmethod
    def validate_record_type(cls, v: str) -> str:
        """Validate record type."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Record type must be non-empty")
        
        record_type_lower = v.strip().lower()
        if record_type_lower not in cls.VALID_RECORD_TYPES:
            raise ValueError(f"Record type must be one of: {cls.VALID_RECORD_TYPES}")
        
        return record_type_lower

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate medical record content."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Content must be non-empty")
        if len(v.strip()) > 10000:
            raise ValueError("Content must be at most 10000 characters long")
        return v.strip()

    @field_validator("record_created_at")
    @classmethod
    def validate_record_created_at(cls, v: str) -> str:
        """Validate record creation datetime."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Record created at must be non-empty")
        
        try:
            # Parse ISO 8601 datetime
            datetime.fromisoformat(v.strip().replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Record created at must be in ISO 8601 format")
        
        return v.strip()

    @field_validator("access_level")
    @classmethod
    def validate_access_level(cls, v: str) -> str:
        """Validate access level."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Access level must be non-empty")
        
        access_level_lower = v.strip().lower()
        if access_level_lower not in cls.VALID_ACCESS_LEVELS:
            raise ValueError(f"Access level must be one of: {cls.VALID_ACCESS_LEVELS}")
        
        return access_level_lower

    def is_private(self) -> bool:
        """Check if the record is private."""
        return self.access_level == "private"

    def is_shared(self) -> bool:
        """Check if the record is shared."""
        return self.access_level == "shared"

    def is_recent(self, days: int = 30) -> bool:
        """Check if the record was created within the specified number of days."""
        try:
            created_datetime = datetime.fromisoformat(self.record_created_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_diff = (now - created_datetime).days
            return days_diff <= days
        except ValueError:
            return False

    def get_record_age_days(self) -> int:
        """Get the age of the record in days."""
        try:
            created_datetime = datetime.fromisoformat(self.record_created_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return (now - created_datetime).days
        except ValueError:
            return 0

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
