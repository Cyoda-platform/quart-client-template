"""
RiskLimit entity for trading platform.

Defines risk control thresholds for accounts and traders with
enforcement at pre-trade and post-trade stages.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class RiskLimit(CyodaEntity):
    """
    Represents a risk limit configuration in the trading system.
    
    Manages risk limit lifecycle: initial_state -> active -> suspended -> archived
    """

    ENTITY_NAME: ClassVar[str] = "RiskLimit"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    limit_type: str = Field(
        ..., alias="limitType", description="NOTIONAL, VAR, LOSS, CONCENTRATION"
    )
    limit_value: float = Field(..., alias="limitValue", description="Limit threshold")
    currency: str = Field(default="USD", description="Limit currency")
    check_frequency: str = Field(
        default="REAL_TIME",
        alias="checkFrequency",
        description="REAL_TIME, DAILY, WEEKLY",
    )
    enforcement_action: str = Field(
        default="BLOCK",
        alias="enforcementAction",
        description="BLOCK, WARN, ALERT",
    )
    current_usage: float = Field(
        default=0.0, alias="currentUsage", description="Current usage against limit"
    )
    usage_percent: float = Field(
        default=0.0, alias="usagePercent", description="Usage as percentage"
    )
    is_active: bool = Field(
        default=True, alias="isActive", description="Whether limit is enforced"
    )
    created_at: str = Field(..., alias="createdAt", description="Creation time")
    updated_at: Optional[str] = Field(
        default=None, alias="updatedAt", description="Last update time"
    )

    def is_breached(self) -> bool:
        return self.usage_percent >= 100.0

    def is_warning(self) -> bool:
        return 80.0 <= self.usage_percent < 100.0

