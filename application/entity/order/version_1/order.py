"""
Order Entity for Cyoda Client Application

Represents an order in the system with create, update, and cancel capabilities
as specified in functional requirements.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order entity represents an order in the system that can be created,
    updated, and cancelled through workflow transitions.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> updated -> cancelled
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required business fields
    customer_id: str = Field(..., description="Customer identifier for the order")
    amount: float = Field(..., description="Order amount (must be greater than 0)")

    # Status field (managed by workflow)
    status: Optional[str] = Field(
        default=None, description="Order status: created, updated, cancelled"
    )

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the order was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the order was last updated (ISO 8601 format)",
    )

    # Optional fields
    description: Optional[str] = Field(
        default=None, description="Optional description of the order"
    )

    # Processing metadata
    processing_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        alias="processingMetadata",
        description="Metadata populated during processing",
    )

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Validate customer_id field according to requirements"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Customer ID is required and must be non-empty")
        if len(v.strip()) < 3:
            raise ValueError("Customer ID must be at least 3 characters long")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate amount field according to requirements"""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        if v > 1000000:  # Reasonable upper limit
            raise ValueError("Amount must be less than or equal to 1,000,000")
        return round(v, 2)  # Round to 2 decimal places

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description field if provided"""
        if v is not None:
            if len(v) > 500:
                raise ValueError("Description must be at most 500 characters long")
            return v.strip() if v.strip() else None
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Order":
        """Validate business logic rules"""
        # Ensure customer_id and amount are valid
        if not self.customer_id:
            raise ValueError("Customer ID is required")
        if self.amount <= 0:
            raise ValueError("Amount must be greater than 0")

        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def set_status(self, new_status: str) -> None:
        """Update order status and timestamp"""
        self.status = new_status
        self.update_timestamp()

    def set_processing_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set processing metadata and update timestamp"""
        if self.processing_metadata is None:
            self.processing_metadata = {}
        self.processing_metadata.update(metadata)
        self.update_timestamp()

    def is_created(self) -> bool:
        """Check if order is in created status"""
        return self.status == "created"

    def is_cancelled(self) -> bool:
        """Check if order is cancelled"""
        return self.status == "cancelled"

    def can_be_updated(self) -> bool:
        """Check if order can be updated (not cancelled)"""
        return self.status != "cancelled"

    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled (created or updated)"""
        return self.status in ["created", "updated"]

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
