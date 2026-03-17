"""
OrderValidationCriterion for institutional trading platform.

Validates orders before submission with pre-trade risk checks.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for orders with pre-trade risk checks.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates orders with pre-trade risk checks",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the order meets all validation criteria.

        Args:
            entity: The order entity to validate
            **kwargs: Additional criteria parameters

        Returns:
            True if the order is valid, False otherwise
        """
        try:
            self.logger.info(
                f"Validating order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            # Validate required fields
            if not order.order_id or not order.symbol or not order.account_id:
                self.logger.warning("Order missing required fields")
                return False

            # Validate order parameters
            if order.quantity <= 0:
                self.logger.warning(f"Invalid quantity: {order.quantity}")
                return False

            # Validate price for limit orders
            if order.order_type == "limit" and (not order.price or order.price <= 0):
                self.logger.warning("Limit order missing valid price")
                return False

            # Pre-trade risk checks
            if order.max_order_size_limit and order.quantity > order.max_order_size_limit:
                self.logger.warning(
                    f"Order quantity {order.quantity} exceeds limit {order.max_order_size_limit}"
                )
                return False

            self.logger.info(
                f"Order {order.order_id} passed all validation checks"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

