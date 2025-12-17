from common.processor.base import CyodaProcessor
from common.entity.cyoda_entity import CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.order.version_1.order import Order
from application.entity.trade.version_1.trade import Trade
from common.service.service import get_entity_service
import logging
import time

class PreTradeCheckProcessor(CyodaProcessor):
    """
    Processor for pre-trade checks.
    """
    async def process(self, entity: CyodaEntity, **kwargs) -> CyodaEntity:
        """
        Processes the order entity for pre-trade checks.
        """
        order = cast_entity(entity, Order)
        logging.info(f"Performing pre-trade checks for order: {order.id}")
        # In a real implementation, we would check for sufficient funds, etc.
        return order

class PostTradeProcessor(CyodaProcessor):
    """
    Processor for post-trade processing.
    """
    async def process(self, entity: CyodaEntity, **kwargs) -> CyodaEntity:
        """
        Processes the order entity for post-trade actions.
        """
        order = cast_entity(entity, Order)
        logging.info(f"Performing post-trade processing for order: {order.id}")
        
        entity_service = get_entity_service()
        trade_data = {
            "order_id": order.id,
            "instrument_id": order.instrument_id,
            "side": order.side,
            "quantity": order.quantity, # In a real scenario, this could be a partial quantity
            "price": order.price, # In a real scenario, this would be the actual execution price
            "trade_time": int(time.time())
        }
        await entity_service.create(Trade.ENTITY_NAME, Trade.ENTITY_VERSION, trade_data)
        
        # In a real implementation, we would also update Position and Portfolio.
        # This will be implemented later when the other entities are created.
        return order

class CancelOrderProcessor(CyodaProcessor):
    """
    Processor for cancelling an order.
    """
    async def process(self, entity: CyodaEntity, **kwargs) -> CyodaEntity:
        """
        Processes the order entity for cancellation.
        """
        order = cast_entity(entity, Order)
        logging.info(f"Cancelling order: {order.id}")
        # In a real implementation, we would send a cancellation request to the exchange.
        return order
