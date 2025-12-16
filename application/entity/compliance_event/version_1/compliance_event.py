from datetime import datetime, timezone
from typing import ClassVar

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class ComplianceEvent(CyodaEntity):
    """
    ComplianceEvent records compliance and regulatory events.
    
    Tracks violations, alerts, and compliance-related activities.
    """

    ENTITY_NAME: ClassVar[str] = "ComplianceEvent"
    ENTITY_VERSION: ClassVar[int] = 1

    event_id: str = Field(..., description="Business identifier for the compliance event")
    type: str = Field(..., description="Event type: VIOLATION, ALERT, BREACH, etc.")
    description: str = Field(..., description="Event description")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Event timestamp"
    )
    account_id: str = Field(..., description="Associated account ID")
    severity: str = Field(default="INFO", description="Event severity: INFO, WARNING, CRITICAL")
    status: str = Field(default="Open", description="Event status")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

