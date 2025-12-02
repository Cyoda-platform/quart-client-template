"""
RiskControl Entity for Real-Time Trading Platform

Represents risk control rules with pre-trade risk checks, position limits,
and exposure monitoring for trading risk management.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class RiskControl(CyodaEntity):
    """
    RiskControl entity represents risk control rules and monitoring.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> active -> monitored
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "RiskControl"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    rule_id: str = Field(..., alias="ruleId", description="Risk rule identifier")
    rule_type: str = Field(
        ...,
        alias="ruleType",
        description="Risk rule type: POSITION_LIMIT, EXPOSURE_LIMIT, CONCENTRATION_LIMIT",
    )
    portfolio_id: str = Field(
        ..., alias="portfolioId", description="Associated portfolio identifier"
    )
    limit_value: float = Field(..., alias="limitValue", description="Risk limit value")
    current_value: float = Field(
        ..., alias="currentValue", description="Current exposure/position value"
    )
    breach_threshold: float = Field(
        ..., alias="breachThreshold", description="Warning threshold percentage (0-100)"
    )

    # Optional fields
    symbol: Optional[str] = Field(
        default=None, description="Specific symbol (if applicable)"
    )
    is_breached: bool = Field(
        default=False, alias="isBreached", description="Breach status flag"
    )

    # Risk monitoring data
    monitoring_data: Optional[Dict[str, Any]] = Field(
        default=None, alias="monitoringData", description="Risk monitoring data"
    )
    alert_data: Optional[Dict[str, Any]] = Field(
        default=None, alias="alertData", description="Risk alert data"
    )

    # Validation constants
    ALLOWED_RULE_TYPES: ClassVar[List[str]] = [
        "POSITION_LIMIT",
        "EXPOSURE_LIMIT",
        "CONCENTRATION_LIMIT",
    ]

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        """Validate rule type"""
        if v not in cls.ALLOWED_RULE_TYPES:
            raise ValueError(f"Rule type must be one of: {cls.ALLOWED_RULE_TYPES}")
        return v

    @field_validator("limit_value", "current_value")
    @classmethod
    def validate_values(cls, v: float) -> float:
        """Validate values are non-negative"""
        if v < 0:
            raise ValueError("Values must be non-negative")
        return v

    @field_validator("breach_threshold")
    @classmethod
    def validate_breach_threshold(cls, v: float) -> float:
        """Validate breach threshold is between 0 and 100"""
        if v < 0 or v > 100:
            raise ValueError("Breach threshold must be between 0 and 100")
        return v

    def calculate_utilization_percentage(self) -> float:
        """Calculate current utilization as percentage of limit"""
        if self.limit_value == 0:
            return 0.0
        return (self.current_value / self.limit_value) * 100

    def is_threshold_breached(self) -> bool:
        """Check if warning threshold is breached"""
        return self.calculate_utilization_percentage() >= self.breach_threshold

    def is_limit_breached(self) -> bool:
        """Check if hard limit is breached"""
        return self.current_value >= self.limit_value

    def update_current_value(self, new_value: float) -> None:
        """Update current value and check for breaches"""
        self.current_value = new_value
        self.is_breached = self.is_limit_breached()
        self.update_timestamp()

    def set_monitoring_data(self, monitoring_data: Dict[str, Any]) -> None:
        """Set monitoring data and update timestamp"""
        self.monitoring_data = monitoring_data
        self.update_timestamp()

    def set_alert_data(self, alert_data: Dict[str, Any]) -> None:
        """Set alert data and update timestamp"""
        self.alert_data = alert_data
        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        # Add calculated fields
        data["utilizationPercentage"] = self.calculate_utilization_percentage()
        data["thresholdBreached"] = self.is_threshold_breached()
        data["limitBreached"] = self.is_limit_breached()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
