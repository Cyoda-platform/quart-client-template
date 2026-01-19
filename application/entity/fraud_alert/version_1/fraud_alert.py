"""
FraudAlert entity for fraud detection in claims platform.

Represents fraud alerts triggered by automated rules or manual review.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class FraudAlert(CyodaEntity):
    """
    FraudAlert represents a fraud detection alert for a claim.

    Tracks fraud rules triggered, severity, and investigation status.
    """

    ENTITY_NAME: ClassVar[str] = "FraudAlert"
    ENTITY_VERSION: ClassVar[int] = 1

    claim_id: str = Field(..., alias="claimId", description="Associated claim ID")
    alert_type: str = Field(..., alias="alertType", description="Type of fraud alert")
    severity: str = Field(..., description="Severity level (LOW, MEDIUM, HIGH)")
    status: str = Field(default="Open", alias="status", description="Alert status")
    description: str = Field(
        ..., alias="description", description="Description of the fraud alert"
    )
    related_claim_ids: List[str] = Field(
        default_factory=list,
        alias="relatedClaimIds",
        description="Related claim IDs",
    )
    rule_triggered: str = Field(
        ..., alias="ruleTriggered", description="Rule that triggered the alert"
    )
    confidence_score: float = Field(
        ..., alias="confidenceScore", description="Confidence score (0-1)"
    )
    assigned_investigator_id: Optional[str] = Field(
        default=None,
        alias="assignedInvestigatorId",
        description="ID of assigned investigator",
    )
    investigation_notes: List[Dict[str, Any]] = Field(
        default_factory=list,
        alias="investigationNotes",
        description="Investigation notes",
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Alert creation timestamp",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the alert was last updated (ISO 8601 format)",
    )

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = ["LOW", "MEDIUM", "HIGH"]
        if v not in allowed:
            raise ValueError(f"Severity must be one of {allowed}")
        return v

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        allowed = ["DUPLICATE_CLAIM", "SUSPICIOUS_METADATA", "PATTERN_MATCH", "OTHER"]
        if v not in allowed:
            raise ValueError(f"Alert type must be one of {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ["Open", "Closed", "Resolved"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "FraudAlert":
        """Validate business logic rules"""
        if self.confidence_score < 0 or self.confidence_score > 1:
            raise ValueError("Confidence score must be between 0 and 1")
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
