"""
Position entity for trading platform.

Represents a trading position for an account/instrument combination with
P&L tracking and position management through workflow states.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position entity representing a trading position.

    Tracks quantity, average price, and realized/unrealized P&L for
    an account's position in a specific instrument.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core position fields
    account_id: str = Field(
        ..., alias="accountId", description="Account ID holding the position"
    )
    instrument_id: str = Field(
        ..., alias="instrumentId", description="ID of the instrument"
    )
    quantity: float = Field(
        ...,
        description="Current position quantity (positive for long, negative for short)",
    )
    average_price: float = Field(
        ..., alias="averagePrice", description="Average price of the position"
    )
    current_price: Optional[float] = Field(
        default=None,
        alias="currentPrice",
        description="Current market price of the instrument",
    )

    # P&L tracking
    unrealized_pnl: Optional[float] = Field(
        default=0.0,
        alias="unrealizedPnl",
        description="Unrealized profit/loss",
    )
    realized_pnl: Optional[float] = Field(
        default=0.0,
        alias="realizedPnl",
        description="Realized profit/loss",
    )

    # Metadata
    last_updated: str = Field(
        ...,
        alias="lastUpdated",
        description="Timestamp of last position update (ISO 8601)",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
