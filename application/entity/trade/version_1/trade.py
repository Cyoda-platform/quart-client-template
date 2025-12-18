"""
Trade entity for trading platform.

Represents executed trades captured from execution reports with full
audit trail and settlement tracking.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    """
    Represents an executed trade in the trading system.
    
    Manages trade lifecycle: initial_state -> captured -> ledger_posted ->
    settled -> archived
    """

    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    trade_id: str = Field(..., alias="tradeId", description="Unique trade identifier")
    order_id: str = Field(..., alias="orderId", description="Related order ID")
    account_id: str = Field(..., alias="accountId", description="Account that traded")
    symbol: str = Field(..., description="Instrument symbol")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., description="Trade quantity")
    price: float = Field(..., description="Execution price")
    trade_time: str = Field(..., alias="tradeTime", description="Execution timestamp")
    settlement_date: str = Field(
        ..., alias="settlementDate", description="Settlement date (T+N)"
    )
    commission: float = Field(default=0.0, description="Commission charged")
    fees: float = Field(default=0.0, description="Other fees")
    gross_amount: float = Field(
        ..., alias="grossAmount", description="Quantity * Price"
    )
    net_amount: float = Field(
        ..., alias="netAmount", description="Gross - Commission - Fees"
    )
    counterparty: Optional[str] = Field(
        default=None, description="Counterparty identifier"
    )
    settlement_status: str = Field(
        default="PENDING", alias="settlementStatus", description="Settlement status"
    )
    created_at: str = Field(..., alias="createdAt", description="Trade capture time")

    def is_settled(self) -> bool:
        return self.settlement_status == "SETTLED"

    def is_pending_settlement(self) -> bool:
        return self.settlement_status == "PENDING"

