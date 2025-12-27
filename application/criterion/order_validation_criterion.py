import logging
from typing import Any

from application.entity.order import Order
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class OrderValidationCriterion(CyodaCriteriaChecker):
    """
    Validates order for completeness and correctness.
    Checks required fields, order type validity, and amount calculations.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates order for completeness and correctness",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if order is valid.

        Args:
            entity: The Order entity to validate
            **kwargs: Additional parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            order = cast_entity(entity, Order)

            if not order.order_id or len(order.order_id.strip()) == 0:
                self.logger.warning("Order validation failed: missing order ID")
                return False

            if order.side.upper() not in ["BUY", "SELL"]:
                self.logger.warning("Order validation failed: invalid side")
                return False

            if order.quantity <= 0:
                self.logger.warning("Order validation failed: invalid quantity")
                return False

            if order.price < 0:
                self.logger.warning("Order validation failed: negative price")
                return False

            if order.order_value < 0:
                self.logger.warning("Order validation failed: negative order value")
                return False

            self.logger.info(f"Order {order.order_id} validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Error validating order: {str(e)}")
            return False
