from typing import Any, ClassVar, Dict

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Portfolio(CyodaEntity):
    """
    Portfolio represents an account's collection of positions.

    Aggregates position data and provides portfolio-level metrics.
    """

    ENTITY_NAME: ClassVar[str] = "Portfolio"
    ENTITY_VERSION: ClassVar[int] = 1

    portfolio_id: str = Field(..., description="Business identifier for the portfolio")
    account_id: str = Field(..., description="Associated account ID")
    total_value: float = Field(default=0.0, description="Total portfolio value")
    total_pnl: float = Field(default=0.0, description="Total profit/loss")
    positions_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of positions by instrument")
    status: str = Field(default="Active", description="Portfolio status")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
