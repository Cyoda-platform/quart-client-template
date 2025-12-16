from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents a holding of an instrument in an account.

    Tracks quantity, cost basis, and profit/loss for each position.
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    position_id: str = Field(..., description="Business identifier for the position")
    account_id: str = Field(..., description="Account holding the position")
    instrument_id: str = Field(..., description="Instrument in the position")
    quantity: float = Field(..., description="Position quantity")
    avg_price: float = Field(..., description="Average purchase price")
    pnl: float = Field(default=0.0, description="Unrealized profit/loss")
    current_price: Optional[float] = Field(None, description="Current market price")
    status: str = Field(default="Open", description="Position status")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
