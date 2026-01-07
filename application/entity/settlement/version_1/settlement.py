"""
Settlement Entity for Enterprise Payment Processing System

Represents a settlement batch for reconciling and processing payment transactions.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Settlement(CyodaEntity):
    """
    Settlement represents a settlement batch for reconciling payment transactions.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> validated ->
    reconciled -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Settlement"
    ENTITY_VERSION: ClassVar[int] = 1

    # Settlement batch fields
    settlement_batch_id: str = Field(..., description="Unique settlement batch ID")
    settlement_date: str = Field(..., description="Settlement date (ISO 8601 format)")
    currency: str = Field(..., description="ISO 4217 currency code")

    # Transaction details
    transaction_ids: List[str] = Field(
        default_factory=list,
        alias="transactionIds",
        description="List of transaction IDs in this settlement",
    )
    total_amount: float = Field(
        default=0.0,
        ge=0,
        alias="totalAmount",
        description="Total settlement amount",
    )
    transaction_count: int = Field(
        default=0,
        ge=0,
        alias="transactionCount",
        description="Number of transactions in settlement",
    )

    # Settlement status
    status: Optional[str] = Field(
        default=None,
        description="Settlement status: PENDING, IN_PROGRESS, COMPLETED, FAILED",
    )
    reconciliation_status: Optional[str] = Field(
        default=None,
        alias="reconciliationStatus",
        description="Reconciliation status: NOT_STARTED, IN_PROGRESS, RECONCILED, DISCREPANCIES",
    )

    # Reconciliation details
    reconciliation_notes: Optional[str] = Field(
        default=None,
        alias="reconciliationNotes",
        description="Notes from reconciliation process",
    )
    discrepancies: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of discrepancies found during reconciliation",
    )

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when settlement was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when settlement was last updated",
    )
    completed_at: Optional[str] = Field(
        default=None,
        alias="completedAt",
        description="Timestamp when settlement was completed",
    )

    # Validation rules
    ALLOWED_CURRENCIES: ClassVar[List[str]] = [
        "USD",
        "EUR",
        "GBP",
        "JPY",
        "CAD",
        "AUD",
        "CHF",
        "CNY",
    ]
    SETTLEMENT_STATUSES: ClassVar[List[str]] = [
        "PENDING",
        "IN_PROGRESS",
        "COMPLETED",
        "FAILED",
    ]
    RECONCILIATION_STATUSES: ClassVar[List[str]] = [
        "NOT_STARTED",
        "IN_PROGRESS",
        "RECONCILED",
        "DISCREPANCIES",
    ]

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code"""
        if v not in cls.ALLOWED_CURRENCIES:
            raise ValueError(f"Currency must be one of: {cls.ALLOWED_CURRENCIES}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate settlement status"""
        if v is not None and v not in cls.SETTLEMENT_STATUSES:
            raise ValueError(f"Status must be one of: {cls.SETTLEMENT_STATUSES}")
        return v

    @field_validator("reconciliation_status")
    @classmethod
    def validate_reconciliation_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate reconciliation status"""
        if v is not None and v not in cls.RECONCILIATION_STATUSES:
            raise ValueError(
                f"Reconciliation status must be one of: {cls.RECONCILIATION_STATUSES}"
            )
        return v

    @model_validator(mode="after")
    def validate_business_logic(self) -> "Settlement":
        """Validate business logic rules"""
        if self.total_amount < 0:
            raise ValueError("Total amount cannot be negative")
        if self.transaction_count < 0:
            raise ValueError("Transaction count cannot be negative")
        return self

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def add_transaction(self, transaction_id: str, amount: float) -> None:
        """Add a transaction to the settlement"""
        if transaction_id not in self.transaction_ids:
            self.transaction_ids.append(transaction_id)
            self.total_amount += amount
            self.transaction_count += 1
            self.update_timestamp()

    def set_reconciliation_result(
        self,
        status: str,
        notes: Optional[str] = None,
        discrepancies: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Set reconciliation results"""
        self.reconciliation_status = status
        self.reconciliation_notes = notes
        self.discrepancies = discrepancies
        self.update_timestamp()

    def mark_completed(self) -> None:
        """Mark settlement as completed"""
        self.status = "COMPLETED"
        self.completed_at = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        self.update_timestamp()

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
