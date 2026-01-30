"""
CatFact entity for Weekly Cat Fact Subscription application.

Represents a cat fact retrieved from the Cat Fact API.
Stores the fact text, retrieval timestamp, and scheduling information.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class CatFact(CyodaEntity):
    """
    CatFact represents a cat fact retrieved from the Cat Fact API.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> retrieved -> scheduled -> sent
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "CatFact"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    fact_text: str = Field(
        ..., alias="factText", description="The cat fact text content"
    )
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="retrievedAt",
        description="Timestamp when fact was retrieved from API (ISO 8601 format)",
    )
    send_date: Optional[str] = Field(
        default=None,
        alias="sendDate",
        description="Date when this fact should be sent to subscribers (ISO 8601 date)",
    )
    source_url: str = Field(
        default="https://catfact.ninja/",
        alias="sourceUrl",
        description="URL of the source API",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the fact (length, category, etc.)",
    )

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the entity was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the entity was last updated (ISO 8601 format)",
    )

    @field_validator("fact_text")
    @classmethod
    def validate_fact_text(cls, v: str) -> str:
        """Validate fact text is non-empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Fact text must be non-empty")
        if len(v) > 5000:
            raise ValueError("Fact text must be at most 5000 characters long")
        return v.strip()

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, v: str) -> str:
        """Validate source URL format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Source URL must be non-empty")
        if not v.startswith("http"):
            raise ValueError("Source URL must start with http or https")
        return v.strip()

    @field_validator("send_date")
    @classmethod
    def validate_send_date(cls, v: Optional[str]) -> Optional[str]:
        """Validate send date format if provided"""
        if v is None:
            return v
        if len(v.strip()) == 0:
            return None
        # Basic ISO 8601 date validation (YYYY-MM-DD)
        if not isinstance(v, str) or len(v) < 10:
            raise ValueError("Send date must be in ISO 8601 format (YYYY-MM-DD)")
        return v.strip()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

