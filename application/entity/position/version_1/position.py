from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents an open position in a security.

    Tracks quantity, cost basis, and current market value.
    States: initial_state -> created -> active -> closed -> completed
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    # Position identification
    position_id: str = Field(..., description="Unique position identifier")
    symbol: str = Field(..., description="Trading symbol")
    account_id: str = Field(..., description="Trading account ID")

    # Position quantities
    quantity: float = Field(..., description="Current position quantity")
    cost_basis: float = Field(..., ge=0, description="Total cost basis")
    average_cost: float = Field(..., ge=0, description="Average cost per unit")

    # Market values
    current_price: float = Field(..., ge=0, description="Current market price")
    market_value: float = Field(..., ge=0, description="Current market value")
    unrealized_pnl: float = Field(default=0, description="Unrealized P&L")
    realized_pnl: float = Field(default=0, description="Realized P&L")

    # Position details
    position_type: str = Field(default="LONG", description="LONG or SHORT")
    open_date: str = Field(..., description="Position open date")
    close_date: Optional[str] = Field(None, description="Position close date")

    # Risk metrics
    delta: Optional[float] = Field(None, description="Delta for derivatives")
    gamma: Optional[float] = Field(None, description="Gamma for derivatives")
    vega: Optional[float] = Field(None, description="Vega for derivatives")
    theta: Optional[float] = Field(None, description="Theta for derivatives")

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
    )
    updated_at: Optional[str] = Field(None, alias="updatedAt")

    ALLOWED_POSITION_TYPES: ClassVar[List[str]] = ["LONG", "SHORT"]

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        return v.upper()

    @field_validator("position_type")
    @classmethod
    def validate_position_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_POSITION_TYPES:
            raise ValueError(
                f"Position type must be one of: {cls.ALLOWED_POSITION_TYPES}"
            )
        return v

    @model_validator(mode="after")
    def validate_position_logic(self) -> "Position":
        if self.quantity == 0 and self.market_value != 0:
            raise ValueError("Market value must be 0 for zero quantity positions")
        if (
            self.average_cost > 0
            and self.cost_basis != self.quantity * self.average_cost
        ):
            raise ValueError("Cost basis must equal quantity * average_cost")
        return self

    def update_market_value(self, current_price: float) -> None:
        self.current_price = current_price
        self.market_value = self.quantity * current_price
        self.unrealized_pnl = self.market_value - self.cost_basis
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def get_pnl_percentage(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
