"""
TradeProcessor

Processes trades, updates orders and positions.
"""

import logging
from typing import Any, List

from application.entity.order.version_1.order import Order
from application.entity.position.version_1.position import Position
from application.entity.trade.version_1.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from common.service.entity_service import EntityResponse, SearchConditionRequest
from services.services import get_entity_service


class TradeProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="TradeProcessor",
            description="Processes trades, updates orders and positions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            trade = cast_entity(entity, Trade)
            self.logger.info(f"Processing trade {trade.trade_id}")

            entity_service = get_entity_service()

            # 1. Update Order
            # Trade.order_id links to Order.order_id (business ID).
            search_order = (
                SearchConditionRequest.builder()
                .equals("order_id", trade.order_id)
                .build()
            )
            orders_resp: List[EntityResponse] = await entity_service.search(
                "Order", search_order
            )

            account_id = None

            if orders_resp:
                order_resp = orders_resp[0]
                order_data = cast_entity(order_resp.data, Order)
                account_id = order_data.account_id

                # Update filled qty
                new_filled = order_data.filled_quantity + trade.quantity
                order_data.filled_quantity = new_filled

                # Check if fully filled
                new_status = order_data.status
                if new_filled >= order_data.quantity:
                    new_status = "FILLED"

                # Save Order update
                order_dict = order_data.model_dump(by_alias=True)
                order_dict["filledQuantity"] = new_filled
                order_dict["status"] = new_status

                # Note: We must be careful about concurrent updates in real system.
                await entity_service.update(
                    entity_id=order_resp.metadata.id,
                    entity=order_dict,
                    entity_class="Order",
                    entity_version="1",
                )
                self.logger.info(
                    f"Updated Order {trade.order_id} status to {new_status}"
                )

            else:
                self.logger.warning(
                    f"Order {trade.order_id} not found for Trade {trade.trade_id}"
                )

            # 2. Update Position
            if account_id:
                search_pos = (
                    SearchConditionRequest.builder()
                    .equals("account_id", account_id)
                    .equals("instrument_id", trade.instrument_id)
                    .build()
                )

                positions_resp = await entity_service.search("Position", search_pos)

                if positions_resp:
                    # Update existing position
                    pos_resp = positions_resp[0]
                    pos = cast_entity(pos_resp.data, Position)

                    # Simple Avg Price calc
                    total_value = (pos.quantity * pos.avg_price) + (
                        trade.quantity * trade.price
                    )
                    new_qty = pos.quantity + trade.quantity
                    new_avg = total_value / new_qty if new_qty > 0 else 0

                    pos_dict = pos.model_dump(by_alias=True)
                    pos_dict["quantity"] = new_qty
                    pos_dict["avgPrice"] = new_avg
                    # PnL logic omitted for brevity

                    await entity_service.update(
                        entity_id=pos_resp.metadata.id,
                        entity=pos_dict,
                        entity_class="Position",
                        entity_version="1",
                    )
                else:
                    # Create new position
                    new_pos = Position(
                        account_id=account_id,
                        instrument_id=trade.instrument_id,
                        quantity=trade.quantity,
                        avg_price=trade.price,
                        realized_pnl=0.0,
                        unrealized_pnl=0.0,
                    )
                    await entity_service.save(
                        entity=new_pos.model_dump(by_alias=True),
                        entity_class="Position",
                        entity_version="1",
                    )
                    self.logger.info(
                        f"Created new Position for {account_id} {trade.instrument_id}"
                    )

            # Mark trade processed
            trade.processing_status = "PROCESSED"

            return trade

        except Exception as e:
            self.logger.error(
                f"Error processing trade {getattr(entity, 'technical_id', 'unknown')}: {str(e)}"
            )
            raise
