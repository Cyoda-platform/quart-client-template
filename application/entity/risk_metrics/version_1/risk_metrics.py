"""
RiskMetrics entity for institutional trading platform.

Manages real-time risk evaluation with position limits, margin checks, and alerts.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class RiskMetrics(CyodaEntity):
    """
    RiskMetrics represents real-time risk evaluation in the trading system.
    
    Tracks position limits, margin requirements, VaR, and risk alerts.
    States: compliant -> warning -> breach
    """

    ENTITY_NAME: ClassVar[str] = "RiskMetrics"
    ENTITY_VERSION: ClassVar[int] = 1

    # Risk identification
    risk_id: str = Field(..., alias="riskId", description="Unique risk metrics identifier")
    account_id: str = Field(..., alias="accountId", description="Trading account ID")
    legal_entity: str = Field(..., alias="legalEntity", description="Legal entity code")
    
    # Position limits
    position_limit: float = Field(
        ..., alias="positionLimit", description="Maximum position size allowed"
    )
    current_position: float = Field(
        ..., alias="currentPosition", description="Current position size"
    )
    position_utilization: Optional[float] = Field(
        default=None, alias="positionUtilization", description="Position utilization percentage"
    )
    
    # Exposure limits
    exposure_limit: float = Field(
        ..., alias="exposureLimit", description="Maximum exposure allowed"
    )
    current_exposure: float = Field(
        ..., alias="currentExposure", description="Current exposure"
    )
    exposure_utilization: Optional[float] = Field(
        default=None, alias="exposureUtilization", description="Exposure utilization percentage"
    )
    
    # Margin and collateral
    margin_requirement: float = Field(
        ..., alias="marginRequirement", description="Total margin requirement"
    )
    available_margin: float = Field(
        ..., alias="availableMargin", description="Available margin"
    )
    margin_utilization: Optional[float] = Field(
        default=None, alias="marginUtilization", description="Margin utilization percentage"
    )
    
    # Risk metrics
    var_95: Optional[float] = Field(
        default=None, alias="var95", description="Value at Risk (95% confidence)"
    )
    var_99: Optional[float] = Field(
        default=None, alias="var99", description="Value at Risk (99% confidence)"
    )
    
    # Alerts and status
    risk_status: str = Field(
        default="compliant", alias="riskStatus", description="Risk status: compliant, warning, breach"
    )
    alerts: Optional[str] = Field(
        default=None, description="Comma-separated list of active alerts"
    )
    
    # Timestamps
    evaluated_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="evaluatedAt",
        description="Risk evaluation timestamp",
    )
    last_breach_at: Optional[str] = Field(
        default=None, alias="lastBreachAt", description="Last breach timestamp"
    )

    @field_validator("position_limit", "current_position")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Validate positive values"""
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v

    @field_validator("risk_status")
    @classmethod
    def validate_risk_status(cls, v: str) -> str:
        """Validate risk status"""
        valid_statuses = ["compliant", "warning", "breach"]
        if v not in valid_statuses:
            raise ValueError(f"Risk status must be one of: {valid_statuses}")
        return v

    def is_compliant(self) -> bool:
        """Check if all limits are compliant"""
        return self.risk_status == "compliant"

    def is_in_warning(self) -> bool:
        """Check if in warning state"""
        return self.risk_status == "warning"

    def is_in_breach(self) -> bool:
        """Check if in breach state"""
        return self.risk_status == "breach"

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

