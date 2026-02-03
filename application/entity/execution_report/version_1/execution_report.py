"""
ExecutionReport entity for tracking order executions.

Represents execution reports: initial_state -> reported -> confirmed -> settled
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class ExecutionReport(CyodaEntity):
    """
    ExecutionReport tracks individual order executions and fills.
    Manages execution lifecycle from reporting through settlement.
    """

    ENTITY_NAME: ClassVar[str] = "ExecutionReport"
    ENTITY_VERSION: ClassVar[int] = 1

    order_id: str = Field(..., alias="orderId", description="Related order ID")
    account_id: str = Field(..., alias="accountId", description="Account ID")
    instrument_id: str = Field(..., alias="instrumentId", description="Security identifier")
    fill_quantity: float = Field(..., alias="fillQuantity", gt=0, description="Quantity filled")
    fill_price: float = Field(..., alias="fillPrice", ge=0, description="Fill price")
    venue: str = Field(..., description="Execution venue")
    exec_time: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="execTime",
        description="Execution timestamp",
    )
    commission: float = Field(default=0.0, description="Commission charged")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
        description="Report creation timestamp",
    )

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True, extra="allow")

