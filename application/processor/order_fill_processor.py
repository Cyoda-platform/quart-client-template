import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.order.version_1.order import Order
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class OrderFillProcessor(CyodaProcessor):
    """Processes order fills and updates order state."""

    def __init__(self) -> None:
        super().__init__(
            name="OrderFillProcessor",
            description="Processes order fills and updates filled quantities",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process order fill.

        Args:
            entity: The Order entity to process
            **kwargs: Additional processing parameters

        Returns:
            Updated order entity
        """
        try:
            order = cast_entity(entity, Order)

            self.logger.info(f"Processing fill for order {order.entity_id}")

            order.filled_quantity = order.quantity
            order.average_fill_price = order.price or 0.0
            order.updated_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(f"Order {order.entity_id} filled successfully")
            return order

        except Exception as e:
            self.logger.error(f"Error processing order fill: {str(e)}")
            raise
