"""
OrderProcessor for trading platform.

Handles order lifecycle management including acknowledgment,
fill processing, and settlement.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order

logger = logging.getLogger(__name__)


class OrderProcessor(CyodaProcessor):
    """Processes order state transitions and lifecycle events."""

    def __init__(self) -> None:
        super().__init__(
            name="OrderProcessor",
            description="Handles order lifecycle management",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process order entity through its lifecycle.

        Args:
            entity: The order entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed order entity
        """
        try:
            order = cast_entity(entity, Order)
            self.logger.info(f"Processing order {order.client_order_id}")

            # Update timestamp
            from datetime import datetime, timezone
            order.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            self.logger.info(f"Order {order.client_order_id} processed successfully")
            return order

        except Exception as e:
            self.logger.error(f"Error processing order: {str(e)}")
            raise

