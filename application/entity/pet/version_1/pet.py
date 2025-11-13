"""
Pet entity for Cyoda Client Application.

Represents a pet from the Swagger Petstore API with fields for name, category,
photo URLs, tags, and status.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Pet(CyodaEntity):
    """
    Pet entity represents a pet from the Swagger Petstore API.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Pet"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from Petstore API
    name: str = Field(..., description="Name of the pet")
    status: Optional[str] = Field(
        default="available",
        description="Pet status in the store (available, pending, sold)",
    )

    # Optional fields from Petstore API
    pet_id: Optional[int] = Field(
        default=None,
        alias="petId",
        description="Pet ID from the Petstore API",
    )
    category: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Category information for the pet",
    )
    photo_urls: Optional[List[str]] = Field(
        default=None,
        alias="photoUrls",
        description="List of photo URLs for the pet",
    )
    tags: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Tags associated with the pet",
    )

    # Processing-related fields
    downloaded_at: Optional[str] = Field(
        default=None,
        alias="downloadedAt",
        description="Timestamp when pet data was downloaded from API",
    )
    processed_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="processedData",
        description="Data enriched during processing",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name field"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        if len(v) > 100:
            raise ValueError("Name must be at most 100 characters long")
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status field"""
        if v is not None:
            allowed_statuses = ["available", "pending", "sold"]
            if v not in allowed_statuses:
                raise ValueError(
                    f"Status must be one of: {allowed_statuses}"
                )
        return v

    def update_timestamp(self) -> None:
        """Update the downloaded_at timestamp to current time"""
        self.downloaded_at = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

    def set_processed_data(self, processed_data: Dict[str, Any]) -> None:
        """Set processed data and update timestamp"""
        self.processed_data = processed_data
        self.update_timestamp()

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

