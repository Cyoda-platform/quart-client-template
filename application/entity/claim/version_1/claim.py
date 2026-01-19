"""
Claim entity for insurance claims management platform.

Represents an insurance claim with submission details, status tracking,
and document management as specified in functional requirements.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

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
    status: str = Field(default="Submitted", description="Current claim status")
    assigned_adjuster_id: Optional[str] = Field(
        default=None, alias="assignedAdjusterId", description="ID of assigned adjuster"
    )
    assigned_queue_id: Optional[str] = Field(
        default=None, alias="assignedQueueId", description="ID of assigned queue"
    )
    fraud_alert_id: Optional[str] = Field(
        default=None, alias="fraudAlertId", description="ID of fraud alert if flagged"
    )
    document_ids: List[str] = Field(
        default_factory=list, alias="documentIds", description="List of document IDs"
    )
    notes: List[Dict[str, Any]] = Field(
        default_factory=list, description="Timeline of notes and events"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        alias="validationErrors",
        description="Validation errors if any",
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the claim was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the claim was last updated (ISO 8601 format)",
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

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ["Submitted", "Validated", "In Review", "Approved", "Denied"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Claim":
        """Validate business logic rules"""
        if self.claim_amount <= 0:
            raise ValueError("Claim amount must be positive")
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

