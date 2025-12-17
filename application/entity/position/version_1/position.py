from typing import ClassVar

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Account ID")
    instrument_id: str = Field(..., description="Instrument ID (technical ID)")
    quantity: float = Field(default=0.0, description="Current quantity")
    avg_price: float = Field(default=0.0, description="Average entry price")
    realized_pnl: float = Field(default=0.0, description="Realized P&L")
    unrealized_pnl: float = Field(default=0.0, description="Unrealized P&L")
