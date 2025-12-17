"""
Fill entity for trading platform.

Represents an execution fill report that confirms an order (or part of an order)
has been executed at a specific price and quantity on an execution venue.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Fill(CyodaEntity):
    """
    Fill entity representing an order execution.

    Captures fill details including order reference, execution price,
    quantity filled, venue, and commission charges for order reconciliation
    and position tracking.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Fill"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core fill fields
    order_id: str = Field(..., alias="orderId", description="Order identifier")
    instrument_id: str = Field(
        ..., alias="instrumentId", description="Identifier of the instrument"
    )
    quantity: float = Field(..., description="Quantity filled")
    fill_price: float = Field(..., alias="fillPrice", description="Execution price")
    fill_timestamp: str = Field(
        ..., alias="fillTimestamp", description="Timestamp of fill execution (ISO 8601)"
    )
    execution_venue: str = Field(
        ..., alias="executionVenue", description="Venue where order was executed"
    )

    # Optional fields
    commission: Optional[float] = Field(
        default=None, description="Commission charged for this fill"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
