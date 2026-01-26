"""
Newsletter entity for the newsletter application.

Represents a weekly newsletter instance containing the cat fact content
and tracking email delivery status.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Newsletter(CyodaEntity):
    """
    Newsletter represents a weekly newsletter instance.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> fetched -> sent -> completed
    """

    ENTITY_NAME: ClassVar[str] = "Newsletter"
    ENTITY_VERSION: ClassVar[int] = 1

    week_of: str = Field(..., description="ISO date of the week (YYYY-MM-DD)")
    cat_fact: str = Field(..., description="The cat fact content for this week")
    sent_count: int = Field(
        default=0,
        alias="sentCount",
        description="Number of emails successfully sent",
    )
    failed_count: int = Field(
        default=0,
        alias="failedCount",
        description="Number of emails that failed to send",
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when newsletter was created (ISO 8601 format)",
    )
    sent_at: Optional[str] = Field(
        default=None,
        alias="sentAt",
        description="Timestamp when newsletter was sent (ISO 8601 format)",
    )

    def is_sent(self) -> bool:
        """Check if newsletter has been sent"""
        return self.state == "sent" or self.state == "completed"

    def mark_sent(self) -> None:
        """Mark newsletter as sent and update timestamp"""
        self.sent_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
