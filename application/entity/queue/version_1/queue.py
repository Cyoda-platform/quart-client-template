"""
Queue entity for claim triage queues in claims platform.

Represents work queues for manual triage and assignment.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Queue(CyodaEntity):
    """
    Queue represents a triage queue for claims.

    Supports configurable queues by claim type, severity, or region.
    """

    ENTITY_NAME: ClassVar[str] = "Queue"
    ENTITY_VERSION: ClassVar[int] = 1

    queue_name: str = Field(..., alias="queueName", description="Name of the queue")
    queue_type: str = Field(..., alias="queueType", description="Type of queue")
    claim_type_filter: Optional[str] = Field(
        default=None, alias="claimTypeFilter", description="Claim type filter"
    )
    severity_filter: Optional[str] = Field(
        default=None, alias="severityFilter", description="Severity filter"
    )
    region_filter: Optional[str] = Field(
        default=None, alias="regionFilter", description="Region filter"
    )
    priority: int = Field(default=1, alias="priority", description="Queue priority")
    status: str = Field(default="ACTIVE", alias="status", description="Queue status")
    assigned_handler_ids: List[str] = Field(
        default_factory=list,
        alias="assignedHandlerIds",
        description="IDs of assigned handlers",
    )
    pending_claim_ids: List[str] = Field(
        default_factory=list,
        alias="pendingClaimIds",
        description="List of pending claim IDs in queue",
    )
    sla_hours: int = Field(..., alias="slaHours", description="SLA in hours")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the queue was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the queue was last updated (ISO 8601 format)",
    )

    @field_validator("queue_type")
    @classmethod
    def validate_queue_type(cls, v: str) -> str:
        allowed = ["TRIAGE", "SEVERITY", "REGION", "CUSTOM"]
        if v not in allowed:
            raise ValueError(f"Queue type must be one of {allowed}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        allowed = ["ACTIVE", "INACTIVE", "PAUSED"]
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if v < 0 or v > 100:
            raise ValueError("Priority must be between 0 and 100")
        return v

    @field_validator("sla_hours")
    @classmethod
    def validate_sla_hours(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("SLA hours must be positive")
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Queue":
        """Validate business logic rules"""
        if self.priority < 0 or self.priority > 100:
            raise ValueError("Priority must be between 0 and 100")
        if self.sla_hours <= 0:
            raise ValueError("SLA hours must be positive")
        return self

    def add_claim(self, claim_id: str) -> None:
        """Add a claim to the queue"""
        if claim_id not in self.pending_claim_ids:
            self.pending_claim_ids.append(claim_id)
        self.update_timestamp()

    def remove_claim(self, claim_id: str) -> None:
        """Remove a claim from the queue"""
        if claim_id in self.pending_claim_ids:
            self.pending_claim_ids.remove(claim_id)
        self.update_timestamp()

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
