"""
Account entity for institutional trading platform.

Represents an account: initial_state -> active -> suspended -> closed
"""

from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Account(CyodaEntity):
    """
    Account represents a trading account with portfolio and risk management.
    Manages account lifecycle from activation through suspension to closure.
    """

    ENTITY_NAME: ClassVar[str] = "Account"
    ENTITY_VERSION: ClassVar[int] = 1

    account_name: str = Field(..., alias="accountName", description="Account name")
    account_type: str = Field(..., alias="accountType", description="Type: PROPRIETARY, CLIENT, HEDGE_FUND")
    cash_balance: float = Field(default=0.0, alias="cashBalance", description="Available cash")
    total_equity: float = Field(default=0.0, alias="totalEquity", description="Total account equity")
    buying_power: float = Field(default=0.0, alias="buyingPower", description="Available buying power")
    margin_requirement: float = Field(default=0.0, alias="marginRequirement", description="Current margin requirement")
    currency: str = Field(default="USD", description="Account currency")
    is_active: bool = Field(default=True, alias="isActive", description="Is account active")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
        description="Account creation timestamp",
    )
    updated_at: Optional[str] = Field(default=None, alias="updatedAt", description="Last update timestamp")

    ACCOUNT_TYPES: ClassVar[List[str]] = ["PROPRIETARY", "CLIENT", "HEDGE_FUND"]

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        if v not in cls.ACCOUNT_TYPES:
            raise ValueError(f"Account type must be one of: {cls.ACCOUNT_TYPES}")
        return v

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True, extra="allow")

