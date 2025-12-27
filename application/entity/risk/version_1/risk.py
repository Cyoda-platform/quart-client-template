from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Risk(CyodaEntity):
    """
    Risk represents risk control metrics and limits for trading.
    Manages position limits, notional exposure, margin requirements, and alerts.
    """

    ENTITY_NAME: ClassVar[str] = "Risk"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    symbol: str = Field(..., description="Trading symbol")
    position_limit: float = Field(
        ..., alias="positionLimit", description="Maximum position size"
    )
    current_position: float = Field(
        ..., alias="currentPosition", description="Current position size"
    )
    notional_limit: float = Field(
        ..., alias="notionalLimit", description="Maximum notional exposure"
    )
    current_notional: float = Field(
        ..., alias="currentNotional", description="Current notional exposure"
    )
    margin_requirement: float = Field(
        ..., alias="marginRequirement", description="Margin requirement"
    )
    margin_utilization: float = Field(
        ..., alias="marginUtilization", description="Margin utilization %"
    )
    risk_level: str = Field(
        default="LOW", alias="riskLevel", description="Risk level: LOW, MEDIUM, HIGH"
    )
    alert_threshold: float = Field(
        default=80.0, alias="alertThreshold", description="Alert threshold %"
    )
    is_alert_triggered: bool = Field(
        default=False, alias="isAlertTriggered", description="Alert triggered flag"
    )
    last_checked: str = Field(
        ..., alias="lastChecked", description="Last check timestamp"
    )

    @field_validator("account_id", "symbol")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("ID must be non-empty")
        return v.strip()

    @field_validator("position_limit", "current_position", "notional_limit")
    @classmethod
    def validate_amounts(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v

    @field_validator("margin_utilization", "alert_threshold")
    @classmethod
    def validate_percentages(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError("Percentage must be between 0 and 100")
        return v

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        valid_levels = ["LOW", "MEDIUM", "HIGH"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Risk level must be one of {valid_levels}")
        return v.upper()

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
