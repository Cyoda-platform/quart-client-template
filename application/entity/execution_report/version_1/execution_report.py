"""
ExecutionReport entity for trading platform.

Represents execution reports from exchange/broker with fill details
and order status updates.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class ExecutionReport(CyodaEntity):
    """
    Represents an execution report in the trading system.
    
    Manages report lifecycle: initial_state -> received -> processed -> archived
    """

    ENTITY_NAME: ClassVar[str] = "ExecutionReport"
    ENTITY_VERSION: ClassVar[int] = 1

    order_id: str = Field(..., alias="orderId", description="Related order ID")
    client_order_id: str = Field(
        ..., alias="clientOrderId", description="Client order ID"
    )
    exchange_order_id: Optional[str] = Field(
        default=None, alias="exchangeOrderId", description="Exchange order ID"
    )
    execution_id: str = Field(
        ..., alias="executionId", description="Unique execution ID"
    )
    symbol: str = Field(..., description="Instrument symbol")
    side: str = Field(..., description="BUY or SELL")
    order_status: str = Field(
        ..., alias="orderStatus", description="NEW, PARTIAL_FILL, FILLED, CANCELLED, REJECTED"
    )
    filled_quantity: float = Field(
        ..., alias="filledQuantity", description="Quantity filled in this report"
    )
    cumulative_quantity: float = Field(
        ..., alias="cumulativeQuantity", description="Total quantity filled"
    )
    remaining_quantity: float = Field(
        ..., alias="remainingQuantity", description="Remaining quantity"
    )
    execution_price: float = Field(
        ..., alias="executionPrice", description="Fill price"
    )
    commission: float = Field(default=0.0, description="Commission on this fill")
    execution_time: str = Field(
        ..., alias="executionTime", description="Execution timestamp"
    )
    rejection_reason: Optional[str] = Field(
        default=None, alias="rejectionReason", description="Reason if rejected"
    )
    text: Optional[str] = Field(
        default=None, description="Additional text/notes"
    )

    def is_filled(self) -> bool:
        return self.order_status == "FILLED"

    def is_partial_fill(self) -> bool:
        return self.order_status == "PARTIAL_FILL"

    def is_rejected(self) -> bool:
        return self.order_status == "REJECTED"

