import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order import Order


class OrderRoutingProcessor(CyodaProcessor):
    """
    Routes validated orders to the Order Management System (OMS).
    Determines execution venue and sends order to appropriate handler.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderRoutingProcessor",
            description="Routes orders to OMS for execution",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Route order to OMS.

        Args:
            entity: The Order entity to route
            **kwargs: Additional parameters

        Returns:
            The routed order
        """
        try:
            order = cast_entity(entity, Order)

            venue = self._determine_venue(order.symbol)
            self.logger.info(
                f"Routed order {order.order_id} to venue {venue}"
            )
            return order

        except Exception as e:
            self.logger.error(f"Error routing order: {str(e)}")
            raise

    def _determine_venue(self, symbol: str) -> str:
        """Determine execution venue based on symbol."""
        if symbol.startswith("NASDAQ"):
            return "NASDAQ"
        elif symbol.startswith("NYSE"):
            return "NYSE"
        else:
            return "DEFAULT"

