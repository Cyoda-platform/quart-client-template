"""
FraudAlert entity for fraud detection in claims platform.

Represents fraud alerts triggered by automated rules or manual review.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class FraudAlert(CyodaEntity):
    """
    FraudAlert represents a fraud detection alert for a claim.
    
    Tracks fraud rules triggered, severity, and investigation status.
    """

    ENTITY_NAME: ClassVar[str] = "FraudAlert"
    ENTITY_VERSION: ClassVar[int] = 1

    claim_id: str = Field(..., description="Associated claim ID")
    alert_type: str = Field(..., description="Type of fraud alert")
    severity: str = Field(..., description="Severity level (LOW, MEDIUM, HIGH)")
    triggered_rules: List[str] = Field(
        default_factory=list, description="Rules that triggered alert"
    )
    rule_details: Dict[str, Any] = Field(
        default_factory=dict, description="Details of triggered rules"
    )
    investigation_status: str = Field(
        default="pending", description="Investigation status"
    )
    investigator_id: Optional[str] = Field(
        default=None, description="ID of assigned investigator"
    )
    investigation_notes: List[str] = Field(
        default_factory=list, description="Investigation notes"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Alert creation timestamp",
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

