from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class RiskControl(CyodaEntity):
    """
    RiskControl manages risk limits and breach monitoring.
    
    Tracks risk metrics and enforces trading limits.
    States: initial_state -> created -> active -> breached -> resolved -> completed
    """

    ENTITY_NAME: ClassVar[str] = "RiskControl"
    ENTITY_VERSION: ClassVar[int] = 1

    # Risk control identification
    risk_id: str = Field(..., description="Unique risk control identifier")
    account_id: str = Field(..., description="Trading account ID")
    risk_type: str = Field(..., description="POSITION_LIMIT, NOTIONAL_LIMIT, VAR_LIMIT, SECTOR_LIMIT")
    
    # Limit configuration
    limit_value: float = Field(..., ge=0, description="Risk limit value")
    current_value: float = Field(..., description="Current risk metric value")
    utilization_percentage: float = Field(default=0, ge=0, le=100, description="Limit utilization %")
    
    # Breach information
    is_breached: bool = Field(default=False, description="Whether limit is breached")
    breach_amount: float = Field(default=0, description="Amount over limit")
    breach_timestamp: Optional[str] = Field(None, description="When breach occurred")
    
    # Thresholds
    warning_threshold: float = Field(default=80, ge=0, le=100, description="Warning threshold %")
    critical_threshold: float = Field(default=95, ge=0, le=100, description="Critical threshold %")
    
    # Actions
    action_on_breach: str = Field(default="ALERT", description="ALERT, RESTRICT, BLOCK")
    auto_remediate: bool = Field(default=False, description="Auto-remediate on breach")
    
    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt"
    )
    updated_at: Optional[str] = Field(None, alias="updatedAt")
    resolved_at: Optional[str] = Field(None, alias="resolvedAt")

    ALLOWED_RISK_TYPES: ClassVar[List[str]] = [
        "POSITION_LIMIT", "NOTIONAL_LIMIT", "VAR_LIMIT", "SECTOR_LIMIT"
    ]
    ALLOWED_ACTIONS: ClassVar[List[str]] = ["ALERT", "RESTRICT", "BLOCK"]

    @field_validator("risk_type")
    @classmethod
    def validate_risk_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_RISK_TYPES:
            raise ValueError(f"Risk type must be one of: {cls.ALLOWED_RISK_TYPES}")
        return v

    @field_validator("action_on_breach")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in cls.ALLOWED_ACTIONS:
            raise ValueError(f"Action must be one of: {cls.ALLOWED_ACTIONS}")
        return v

    @model_validator(mode="after")
    def validate_risk_logic(self) -> "RiskControl":
        if self.warning_threshold > self.critical_threshold:
            raise ValueError("Warning threshold cannot exceed critical threshold")
        if self.limit_value > 0:
            self.utilization_percentage = (self.current_value / self.limit_value) * 100
        return self

    def check_breach(self) -> bool:
        if self.limit_value <= 0:
            return False
        self.utilization_percentage = (self.current_value / self.limit_value) * 100
        self.is_breached = self.utilization_percentage > 100
        if self.is_breached:
            self.breach_amount = self.current_value - self.limit_value
            self.breach_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return self.is_breached

    def is_warning_level(self) -> bool:
        return self.utilization_percentage >= self.warning_threshold

    def is_critical_level(self) -> bool:
        return self.utilization_percentage >= self.critical_threshold

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

