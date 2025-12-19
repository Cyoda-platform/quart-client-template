from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Account(CyodaEntity):
    """
    Account represents a trading account with risk limits and compliance settings.
    State transitions: initial_state -> active -> suspended/closed
    """

    ENTITY_NAME: ClassVar[str] = "Account"
    ENTITY_VERSION: ClassVar[int] = 1

    account_number: str = Field(..., description="Unique account number")
    account_type: str = Field(
        ..., description="Account type: INDIVIDUAL, INSTITUTIONAL"
    )
    owner_name: str = Field(..., description="Account owner name")
    cash_balance: float = Field(..., ge=0, description="Available cash")
    buying_power: float = Field(..., ge=0, description="Buying power")
    margin_limit: float = Field(..., ge=0, description="Margin limit")
    day_trading_limit: float = Field(..., ge=0, description="Day trading buying power")
    risk_limit: float = Field(..., ge=0, description="Daily loss limit")
    is_margin_enabled: bool = Field(default=False, description="Margin trading enabled")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Account creation timestamp",
    )
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        if v not in ["INDIVIDUAL", "INSTITUTIONAL"]:
            raise ValueError("account_type must be INDIVIDUAL or INSTITUTIONAL")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
