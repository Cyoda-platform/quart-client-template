"""
OrderExecutionProcessor for order execution handling.

Processes order fills and updates position records.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.order.version_1.order import Order
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class OrderExecutionProcessor(CyodaProcessor):
    """Processes order executions and updates positions."""

    def __init__(self) -> None:
        super().__init__(name="OrderExecutionProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process order execution.

        Args:
            entity: The order entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed order entity
        """
        try:
            self.logger.info(
                f"Processing order execution {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            # Simulate execution: fill entire order at market price
            if order.order_type == "MARKET":
                order.filled_quantity = order.quantity
                order.avg_fill_price = order.price or 100.0
            else:
                # For limit orders, assume partial fill
                order.filled_quantity = min(order.quantity * 0.5, order.quantity)
                order.avg_fill_price = order.price

            order.updated_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(
                f"Order {order.technical_id} executed: {order.filled_quantity} shares"
            )
            return order

        except Exception as e:
            self.logger.error(f"Error processing order execution: {str(e)}")
            raise
