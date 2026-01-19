"""
Claim entity for insurance claims management platform.

Represents an insurance claim with submission details, status tracking,
and document management as specified in functional requirements.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Claim(CyodaEntity):
    """
    Claim represents an insurance claim with all submission and tracking details.
    
    Workflow states: initial_state -> submitted -> validated -> fraud_check_complete
    -> ready_for_triage -> in_review -> assigned -> in_assessment -> approved/denied
    """

    ENTITY_NAME: ClassVar[str] = "Claim"
    ENTITY_VERSION: ClassVar[int] = 1

    claim_number: str = Field(..., description="Unique claim number")
    policy_id: str = Field(..., description="Associated policy ID")
    claimant_id: str = Field(..., description="ID of the claimant")
    incident_date: str = Field(..., description="Date/time of incident (ISO 8601)")
    incident_location: str = Field(..., description="Location of incident")
    incident_description: str = Field(..., description="Description of incident")
    claim_type: str = Field(..., description="Type of claim (AUTO, HOME, etc.)")
    claim_amount: float = Field(..., description="Claimed amount")
    assigned_adjuster_id: Optional[str] = Field(
        default=None, description="ID of assigned adjuster"
    )
    assigned_queue_id: Optional[str] = Field(
        default=None, description="ID of assigned queue"
    )
    fraud_alert_id: Optional[str] = Field(
        default=None, description="ID of fraud alert if flagged"
    )
    document_ids: List[str] = Field(
        default_factory=list, description="List of document IDs"
    )
    notes: List[Dict[str, Any]] = Field(
        default_factory=list, description="Timeline of notes and events"
    )
    validation_errors: List[str] = Field(
        default_factory=list, description="Validation errors if any"
    )

    @field_validator("claim_type")
    @classmethod
    def validate_claim_type(cls, v: str) -> str:
        allowed = ["AUTO", "HOME", "LIFE", "HEALTH"]
        if v not in allowed:
            raise ValueError(f"Claim type must be one of {allowed}")
        return v

    @field_validator("claim_amount")
    @classmethod
    def validate_claim_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Claim amount must be positive")
        return v

