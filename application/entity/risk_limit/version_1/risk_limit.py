"""
RiskLimit entity for trading platform.

Represents risk control limits for pre-trade and real-time risk management.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class RiskLimit(CyodaEntity):
    """
    RiskLimit entity representing risk control limits.

    Supports order size limits, position limits, max notional,
    and instrument restrictions for pre-trade and real-time risk controls.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "RiskLimit"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core risk limit fields
    account_id: str = Field(
        ..., alias="accountId", description="Account ID for the risk limit"
    )
    limit_type: str = Field(
        ...,
        alias="limitType",
        description="Type of limit: ORDER_SIZE, POSITION, MAX_NOTIONAL, INSTRUMENT_RESTRICTION",
    )
    instrument_id: Optional[str] = Field(
        default=None,
        alias="instrumentId",
        description="Instrument ID (if limit is instrument-specific)",
    )

    # Limit values
    max_order_quantity: Optional[float] = Field(
        default=None, alias="maxOrderQuantity", description="Maximum order quantity"
    )
    max_position_quantity: Optional[float] = Field(
        default=None,
        alias="maxPositionQuantity",
        description="Maximum position quantity",
    )
    max_notional: Optional[float] = Field(
        default=None, alias="maxNotional", description="Maximum notional value"
    )

    # Status
    is_active: bool = Field(
        default=True, alias="isActive", description="Whether limit is active"
    )
    breach_action: str = Field(
        default="REJECT",
        alias="breachAction",
        description="Action on breach: REJECT, WARN, THROTTLE",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
