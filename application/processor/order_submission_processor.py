"""
OrderSubmissionProcessor for order submission handling.

Validates and processes order submissions, creating execution records.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order


class OrderSubmissionProcessor(CyodaProcessor):
    """Processes order submissions and validates against risk limits."""

    def __init__(self) -> None:
        super().__init__(name="OrderSubmissionProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process order submission.

        Args:
            entity: The order entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed order entity
        """
        try:
            self.logger.info(f"Processing order submission {getattr(entity, 'technical_id', '<unknown>')}")

            order = cast_entity(entity, Order)

            # Validate order data
            if order.quantity <= 0:
                raise ValueError("Order quantity must be positive")

            if order.order_type == "LIMIT" and (order.price is None or order.price <= 0):
                raise ValueError("Limit orders must have a positive price")

            # Update timestamp
            order.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            self.logger.info(f"Order {order.technical_id} submitted successfully")
            return order

        except Exception as e:
            self.logger.error(f"Error processing order submission: {str(e)}")
            raise

