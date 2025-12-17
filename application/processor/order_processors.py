import logging
import time
from typing import Any

from application.entity.order.version_1.order import Order, OrderSide
from application.entity.position.version_1.position import Position
from application.entity.trade.version_1.trade import Trade
from common.entity.cyoda_entity import CyodaEntity
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaProcessor
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service


class PreTradeCheckProcessor(CyodaProcessor):
    """
    Processor for pre-trade checks.
    """

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Processes the order entity for pre-trade checks.
        """
        order = cast_entity(entity, Order)
        logging.info(f"Performing pre-trade checks for order: {entity.get_id()}")
        # In a real implementation, we would check for sufficient funds, etc.
        return order


class PostTradeProcessor(CyodaProcessor):
    """
    Processor for post-trade processing.
    """

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Processes the order entity for post-trade actions.
        """
        order = cast_entity(entity, Order)
        logging.info(f"Performing post-trade processing for order: {entity.get_id()}")

        entity_service = get_entity_service()

        # In a real scenario, the execution price should come from the exchange
        execution_price = order.price if order.price is not None else 1.0

        trade_data = {
            "order_id": entity.get_id(),
            "instrument_id": order.instrument_id,
            "side": order.side,
            "quantity": order.quantity,  # In a real scenario, this could be a partial quantity
            "price": execution_price,
            "trade_time": int(time.time()),
        }
        await entity_service.save(trade_data, Trade.ENTITY_NAME, Trade.ENTITY_VERSION)

        # Update Position
        search_request = (
            SearchConditionRequest.builder()
            .equals("instrument_id", order.instrument_id)
            .equals("portfolio_id", order.portfolio_id)
            .build()
        )

        positions_responses = await entity_service.search(
            Position.ENTITY_NAME, search_request, Position.ENTITY_VERSION
        )

        if positions_responses:
            # Position exists, update it
            position_response = positions_responses[0]
            position = cast_entity(position_response.data, Position)

            if order.side == OrderSide.BUY:
                new_quantity = position.quantity + order.quantity
                new_avg_price = (
                    (position.average_price * position.quantity)
                    + (execution_price * order.quantity)
                ) / new_quantity
            else:  # SELL
                new_quantity = position.quantity - order.quantity
                new_avg_price = (
                    position.average_price
                )  # Average price doesn't change on sell

            position.quantity = new_quantity
            position.average_price = new_avg_price

            await entity_service.update(
                position_response.get_id(),
                position.model_dump(exclude_unset=True),
                Position.ENTITY_NAME,
                entity_version=Position.ENTITY_VERSION,
            )
        else:
            # Position does not exist, create it
            position_data = {
                "portfolio_id": order.portfolio_id,
                "instrument_id": order.instrument_id,
                "quantity": (
                    order.quantity if order.side == OrderSide.BUY else -order.quantity
                ),
                "average_price": execution_price,
            }
            await entity_service.save(
                position_data, Position.ENTITY_NAME, Position.ENTITY_VERSION
            )

        return order


class CancelOrderProcessor(CyodaProcessor):
    """
    Processor for cancelling an order.
    """

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Processes the order entity for cancellation.
        """
        order = cast_entity(entity, Order)
        logging.info(f"Cancelling order: {entity.get_id()}")
        # In a real implementation, we would send a cancellation request to the exchange.
        return order
