"""
LedgerEntry entity for institutional trading platform.

Represents cash accounting entries for accounts.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class LedgerEntry(CyodaEntity):
    """
    LedgerEntry represents a cash accounting entry.

    State: initial_state -> created -> settled
    """

    ENTITY_NAME: ClassVar[str] = "LedgerEntry"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    entry_type: str = Field(
        ...,
        alias="entryType",
        description="TRADE, COMMISSION, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL",
    )
    amount: float = Field(..., description="Entry amount")
    currency: str = Field(default="USD", description="Currency code")
    reference_id: Optional[str] = Field(
        default=None, alias="referenceId", description="Reference to trade/order"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Creation timestamp",
    )

    @field_validator("entry_type")
    @classmethod
    def validate_entry_type(cls, v: str) -> str:
        valid = {
            "TRADE",
            "COMMISSION",
            "DIVIDEND",
            "INTEREST",
            "DEPOSIT",
            "WITHDRAWAL",
        }
        if v.upper() not in valid:
            raise ValueError(f"Invalid entry type: {v}")
        return v.upper()
