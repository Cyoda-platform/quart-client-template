"""
RiskProfile entity for institutional trading platform.

Represents risk controls and limits for accounts.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class RiskProfile(CyodaEntity):
    """
    RiskProfile represents risk controls and limits.
    
    State: initial_state -> active -> breached -> resolved
    """

    ENTITY_NAME: ClassVar[str] = "RiskProfile"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    max_position_size: float = Field(
        ..., alias="maxPositionSize", description="Max position size"
    )
    max_daily_loss: float = Field(
        ..., alias="maxDailyLoss", description="Max daily loss limit"
    )
    max_leverage: float = Field(
        default=1.0, alias="maxLeverage", description="Max leverage ratio"
    )
    current_loss: float = Field(
        default=0.0, alias="currentLoss", description="Current daily loss"
    )
    breach_count: int = Field(
        default=0, alias="breachCount", description="Number of breaches"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Creation timestamp",
    )

    @field_validator("max_position_size")
    @classmethod
    def validate_max_position_size(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Max position size must be positive")
        return v

    @field_validator("max_daily_loss")
    @classmethod
    def validate_max_daily_loss(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Max daily loss must be positive")
        return v

