"""
OrderRouter processor for institutional trading platform.

Routes orders to appropriate execution venues based on rules.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order import Order


class OrderRouter(CyodaProcessor):
    """
    Routes orders to execution venues based on order characteristics
    and routing rules.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderRouter",
            description="Routes orders to appropriate execution venues",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Route the order based on order type, size, and market conditions.

        Args:
            entity: The Order entity to route

        Returns:
            The routed order entity
        """
        try:
            self.logger.info(
                f"Routing order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            # Determine routing based on order characteristics
            routing_venue = self._determine_routing_venue(order)
            order.routing_venue = routing_venue

            self.logger.info(
                f"Order {order.technical_id} routed to {routing_venue}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error routing order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _determine_routing_venue(self, order: Order) -> str:
        """
        Determine the routing venue based on order characteristics.

        Args:
            order: The order to route

        Returns:
            The routing venue name
        """
        if order.order_type == "MARKET":
            return "PRIMARY_EXCHANGE"
        elif order.quantity > 10000:
            return "DARK_POOL"
        else:
            return "SMART_ROUTER"

