"""
Queue entity for claim triage queues in claims platform.

Represents work queues for manual triage and assignment.
"""

from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Queue(CyodaEntity):
    """
    Queue represents a triage queue for claims.
    
    Supports configurable queues by claim type, severity, or region.
    """

    ENTITY_NAME: ClassVar[str] = "Queue"
    ENTITY_VERSION: ClassVar[int] = 1

    queue_name: str = Field(..., description="Name of the queue")
    queue_type: str = Field(..., description="Type (CLAIM_TYPE, SEVERITY, REGION)")
    filter_criteria: str = Field(..., description="Filter criteria for queue")
    claim_ids: List[str] = Field(
        default_factory=list, description="List of claim IDs in queue"
    )
    assigned_handler_ids: List[str] = Field(
        default_factory=list, description="IDs of assigned handlers"
    )
    priority: int = Field(default=0, description="Queue priority")
    is_active: bool = Field(default=True, description="Whether queue is active")

    @field_validator("queue_type")
    @classmethod
    def validate_queue_type(cls, v: str) -> str:
        allowed = ["CLAIM_TYPE", "SEVERITY", "REGION", "CUSTOM"]
        if v not in allowed:
            raise ValueError(f"Queue type must be one of {allowed}")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if v < 0 or v > 100:
            raise ValueError("Priority must be between 0 and 100")
        return v

    def add_claim(self, claim_id: str) -> None:
        """Add a claim to the queue"""
        if claim_id not in self.claim_ids:
            self.claim_ids.append(claim_id)

    def remove_claim(self, claim_id: str) -> None:
        """Remove a claim from the queue"""
        if claim_id in self.claim_ids:
            self.claim_ids.remove(claim_id)

