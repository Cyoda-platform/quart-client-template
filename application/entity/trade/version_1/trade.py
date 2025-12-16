from datetime import datetime, timezone
from typing import ClassVar

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    """
    Trade represents an executed trade between a buyer and seller.
    
    Records the matching of buy and sell orders with execution details
    including price, quantity, and execution timestamp.
    """

    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    trade_id: str = Field(..., description="Unique trade identifier")
    buy_order_id: str = Field(..., description="Buying order identifier")
    sell_order_id: str = Field(..., description="Selling order identifier")
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTC/USD)")
    price: float = Field(..., description="Execution price")
    quantity: float = Field(..., description="Executed quantity")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Trade execution timestamp (ISO 8601 format)"
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate price is positive"""
        if v <= 0:
            raise ValueError("Price must be positive")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        """Validate quantity is positive"""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    def get_notional_value(self) -> float:
        """Calculate total notional value of trade"""
        return self.price * self.quantity

