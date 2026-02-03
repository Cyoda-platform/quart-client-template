"""
OrderCompletionProcessor for order completion handling.

Finalizes order processing and generates execution reports.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order


class OrderCompletionProcessor(CyodaProcessor):
    """Completes order processing and generates reports."""

    def __init__(self) -> None:
        super().__init__(name="OrderCompletionProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Complete order processing.

        Args:
            entity: The order entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed order entity
        """
        try:
            self.logger.info(f"Completing order {getattr(entity, 'technical_id', '<unknown>')}")

            order = cast_entity(entity, Order)

            # Verify order is fully filled
            if order.filled_quantity < order.quantity:
                self.logger.warning(f"Order {order.technical_id} not fully filled")

            order.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            self.logger.info(f"Order {order.technical_id} completed")
            return order

        except Exception as e:
            self.logger.error(f"Error completing order: {str(e)}")
            raise

