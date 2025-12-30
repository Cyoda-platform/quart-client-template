"""
Account entity for institutional trading platform.

Represents trading accounts with cash and margin tracking.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Account(CyodaEntity):
    """
    Account represents a trading account.
    
    State: initial_state -> active -> suspended -> closed
    """

    ENTITY_NAME: ClassVar[str] = "Account"
    ENTITY_VERSION: ClassVar[int] = 1

    account_number: str = Field(..., alias="accountNumber", description="Account number")
    account_name: str = Field(..., alias="accountName", description="Account name")
    currency: str = Field(default="USD", description="Base currency")
    cash_balance: float = Field(
        default=0.0, alias="cashBalance", description="Available cash"
    )
    margin_balance: float = Field(
        default=0.0, alias="marginBalance", description="Margin available"
    )
    total_equity: Optional[float] = Field(
        default=None, alias="totalEquity", description="Total account equity"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Creation timestamp",
    )

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Account number must be non-empty")
        return v.strip()

    @field_validator("account_name")
    @classmethod
    def validate_account_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Account name must be non-empty")
        return v.strip()

