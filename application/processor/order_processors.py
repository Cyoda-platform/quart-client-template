from common.processor.base import CyodaProcessor
from common.entity.cyoda_entity import CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.order.version_1.order import Order
import logging

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
        # In a real implementation, we would create a Trade entity, and update Position and Portfolio.
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
