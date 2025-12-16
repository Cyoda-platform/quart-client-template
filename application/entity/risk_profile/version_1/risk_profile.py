from typing import ClassVar, Optional

from pydantic import BaseModel, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Limits(BaseModel):
    """Position and notional limits"""

    max_position: float = Field(..., description="Maximum position size per symbol")
    max_notional: float = Field(..., description="Maximum notional exposure per symbol")


class MarginRequirements(BaseModel):
    """Margin requirement specifications"""

    initial_margin_rate: float = Field(
        ..., description="Initial margin requirement as percentage"
    )
    maintenance_margin_rate: float = Field(
        ..., description="Maintenance margin requirement as percentage"
    )


class RiskProfile(CyodaEntity):
    """
    RiskProfile defines risk limits and margin requirements for an account.

    Manages position limits, notional exposure caps, margin requirements,
    and current exposure tracking for risk management.
    """

    ENTITY_NAME: ClassVar[str] = "RiskProfile"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Account identifier")
    limits: Limits = Field(..., description="Position and notional limits")
    margin_requirements: MarginRequirements = Field(
        ..., description="Margin requirement specifications"
    )
    current_exposure: float = Field(
        default=0.0, description="Current total notional exposure across all positions"
    )

    @field_validator("current_exposure")
    @classmethod
    def validate_current_exposure(cls, v: float) -> float:
        """Validate current exposure is non-negative"""
        if v < 0:
            raise ValueError("Current exposure cannot be negative")
        return v

    def is_within_limits(self, proposed_notional: float) -> bool:
        """Check if proposed notional exposure is within limits"""
        return (self.current_exposure + proposed_notional) <= self.limits.max_notional

    def get_available_notional(self) -> float:
        """Calculate available notional capacity"""
        return max(0, self.limits.max_notional - self.current_exposure)

    def get_margin_utilization(self, account_equity: float) -> float:
        """Calculate margin utilization percentage"""
        if account_equity <= 0:
            return 0.0
        required_margin = account_equity * self.margin_requirements.initial_margin_rate
        return (
            (self.current_exposure / required_margin) * 100
            if required_margin > 0
            else 0.0
        )
