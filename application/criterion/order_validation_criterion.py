"""
OrderValidationCriterion for order validation.

Validates orders before acceptance.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriteriaChecker):
    """Validates orders before acceptance."""

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates order data and business rules",
        )
        self.logger = logging.getLogger(__name__)

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if order meets validation criteria.

        Args:
            entity: The order entity to validate
            **kwargs: Additional criteria parameters

        Returns:
            True if order is valid, False otherwise
        """
        try:
            self.logger.info(f"Validating order {getattr(entity, 'technical_id', '<unknown>')}")

            order = cast_entity(entity, Order)

            # Validate required fields
            if not order.account_id or not order.instrument_id:
                self.logger.warning(f"Order {order.technical_id} missing required fields")
                return False

            # Validate order type
            if order.order_type not in order.ORDER_TYPES:
                self.logger.warning(f"Order {order.technical_id} invalid order type")
                return False

            # Validate side
            if order.side not in order.SIDES:
                self.logger.warning(f"Order {order.technical_id} invalid side")
                return False

            # Validate quantity
            if order.quantity <= 0:
                self.logger.warning(f"Order {order.technical_id} invalid quantity")
                return False

            # Validate price for limit orders
            if order.order_type == "LIMIT" and (order.price is None or order.price <= 0):
                self.logger.warning(f"Order {order.technical_id} invalid limit price")
                return False

            self.logger.info(f"Order {order.technical_id} passed validation")
            return True

        except Exception as e:
            self.logger.error(f"Error validating order: {str(e)}")
            return False

