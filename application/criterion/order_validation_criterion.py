"""
OrderValidationCriterion for trading platform.

Validates order data before submission to execution gateway.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriteriaChecker):
    """Validates order business rules before execution."""

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates order data and business rules",
        )

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
            order = cast_entity(entity, Order)
            self.logger.info(f"Validating order {order.client_order_id}")

            # Validate required fields
            if not order.symbol or len(order.symbol) == 0:
                self.logger.warning("Order missing symbol")
                return False

            if order.quantity <= 0:
                self.logger.warning("Order quantity must be positive")
                return False

            if order.side not in ("BUY", "SELL"):
                self.logger.warning(f"Invalid order side: {order.side}")
                return False

            if order.order_type not in ("MARKET", "LIMIT", "STOP"):
                self.logger.warning(f"Invalid order type: {order.order_type}")
                return False

            # Validate limit price if LIMIT order
            if order.order_type == "LIMIT" and (order.price is None or order.price <= 0):
                self.logger.warning("LIMIT order missing valid price")
                return False

            self.logger.info(f"Order {order.client_order_id} validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Error validating order: {str(e)}")
            return False

