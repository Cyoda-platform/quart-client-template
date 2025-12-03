# entity/risk_control/version_1/risk_control.py

"""
RiskControl Entity for Trading Platform

Represents risk limits and real-time monitoring for trading activities.
Manages risk thresholds, exposure tracking, and breach notifications.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class RiskControl(CyodaEntity):
    """
    RiskControl represents risk limits and real-time monitoring
    for trading activities with automatic breach detection.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "RiskControl"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core identification
    client_id: str = Field(..., alias="clientId", description="Client identifier")
    limit_name: str = Field(..., alias="limitName", description="Risk limit name")
    limit_type: str = Field(..., alias="limitType", description="Type of risk limit")

    # Limit configuration
    limit_value: Decimal = Field(..., alias="limitValue", description="Maximum allowed value")
    warning_threshold: Decimal = Field(..., alias="warningThreshold", description="Warning threshold (percentage of limit)")
    breach_threshold: Decimal = Field(..., alias="breachThreshold", description="Breach threshold (percentage of limit)")

    # Current status
    current_exposure: Decimal = Field(default=Decimal("0"), alias="currentExposure", description="Current exposure value")
    utilization_percentage: Decimal = Field(default=Decimal("0"), alias="utilizationPercentage", description="Current utilization percentage")
    
    # Status flags
    is_active: bool = Field(default=True, alias="isActive", description="Whether limit is active")
    is_breached: bool = Field(default=False, alias="isBreached", description="Whether limit is currently breached")
    warning_triggered: bool = Field(default=False, alias="warningTriggered", description="Whether warning threshold triggered")

    # Breach tracking
    breach_count: int = Field(default=0, alias="breachCount", description="Number of breaches")
    last_breach_time: Optional[str] = Field(default=None, alias="lastBreachTime", description="Last breach timestamp")
    breach_reason: Optional[str] = Field(default=None, alias="breachReason", description="Reason for last breach")

    # Timestamps
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
        description="Risk control creation timestamp"
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="lastUpdated",
        description="Last update timestamp"
    )

    # Validation constants
    VALID_LIMIT_TYPES: ClassVar[List[str]] = [
        "POSITION_LIMIT", "EXPOSURE_LIMIT", "LOSS_LIMIT", "CONCENTRATION_LIMIT",
        "LEVERAGE_LIMIT", "VAR_LIMIT", "NOTIONAL_LIMIT", "ORDER_SIZE_LIMIT"
    ]

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Validate client ID"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Client ID must be non-empty")
        return v.strip()

    @field_validator("limit_type")
    @classmethod
    def validate_limit_type(cls, v: str) -> str:
        """Validate limit type"""
        if v not in cls.VALID_LIMIT_TYPES:
            raise ValueError(f"Limit type must be one of: {cls.VALID_LIMIT_TYPES}")
        return v

    @field_validator("limit_value")
    @classmethod
    def validate_limit_value(cls, v: Decimal) -> Decimal:
        """Validate limit value"""
        if v <= 0:
            raise ValueError("Limit value must be positive")
        return v

    @field_validator("warning_threshold")
    @classmethod
    def validate_warning_threshold(cls, v: Decimal) -> Decimal:
        """Validate warning threshold"""
        if v <= 0 or v > 100:
            raise ValueError("Warning threshold must be between 0 and 100")
        return v

    @field_validator("breach_threshold")
    @classmethod
    def validate_breach_threshold(cls, v: Decimal) -> Decimal:
        """Validate breach threshold"""
        if v <= 0 or v > 100:
            raise ValueError("Breach threshold must be between 0 and 100")
        return v

    def update_exposure(self, current_exposure: Decimal) -> None:
        """Update current exposure and check thresholds"""
        self.current_exposure = current_exposure
        self.utilization_percentage = (current_exposure / self.limit_value) * 100
        
        # Check thresholds
        warning_level = (self.warning_threshold / 100) * self.limit_value
        breach_level = (self.breach_threshold / 100) * self.limit_value
        
        # Update warning status
        self.warning_triggered = current_exposure >= warning_level
        
        # Check for breach
        if current_exposure >= breach_level and not self.is_breached:
            self.trigger_breach(f"Exposure {current_exposure} exceeds breach threshold {breach_level}")
        elif current_exposure < breach_level and self.is_breached:
            self.resolve_breach()
        
        self.update_timestamp()

    def trigger_breach(self, reason: str) -> None:
        """Trigger a risk limit breach"""
        self.is_breached = True
        self.breach_count += 1
        self.last_breach_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self.breach_reason = reason
        self.update_timestamp()

    def resolve_breach(self) -> None:
        """Resolve a risk limit breach"""
        self.is_breached = False
        self.breach_reason = None
        self.update_timestamp()

    def set_limit_value(self, new_limit: Decimal) -> None:
        """Update the limit value"""
        self.limit_value = new_limit
        # Recalculate utilization with new limit
        self.utilization_percentage = (self.current_exposure / self.limit_value) * 100
        self.update_timestamp()

    def set_thresholds(self, warning_threshold: Decimal, breach_threshold: Decimal) -> None:
        """Update warning and breach thresholds"""
        self.warning_threshold = warning_threshold
        self.breach_threshold = breach_threshold
        # Re-evaluate current status
        self.update_exposure(self.current_exposure)

    def activate(self) -> None:
        """Activate the risk control"""
        self.is_active = True
        self.update_timestamp()

    def deactivate(self) -> None:
        """Deactivate the risk control"""
        self.is_active = False
        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the last_updated timestamp"""
        self.last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def get_remaining_capacity(self) -> Decimal:
        """Get remaining capacity before breach"""
        breach_level = (self.breach_threshold / 100) * self.limit_value
        return max(Decimal("0"), breach_level - self.current_exposure)

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        data["remainingCapacity"] = self.get_remaining_capacity()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
