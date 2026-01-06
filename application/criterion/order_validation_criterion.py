"""
OrderValidationCriterion validates orders before submission.

Checks order format, pricing logic, and basic compliance.
"""

import logging
from typing import Any

from application.entity.order import Order
from common.criterion.base import CyodaCriterion, CyodaEntity
from common.entity.entity_casting import cast_entity


class OrderValidationCriterion(CyodaCriterion):
    """Validates order data and business rules."""

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates order data and business rules",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """Evaluate if order is valid."""
        try:
            order = cast_entity(entity, Order)

            # Validate order structure
            if not self._validate_order_structure(order):
                self.logger.warning(
                    f"Order {order.order_id} failed structure validation"
                )
                return False

            # Validate pricing logic
            if not self._validate_pricing(order):
                self.logger.warning(f"Order {order.order_id} failed pricing validation")
                return False

            # Validate quantity
            if not self._validate_quantity(order):
                self.logger.warning(
                    f"Order {order.order_id} failed quantity validation"
                )
                return False

            self.logger.info(f"Order {order.order_id} passed validation")
            return True

        except Exception as e:
            self.logger.error(f"Error validating order: {str(e)}")
            return False

    def _validate_order_structure(self, order: Order) -> bool:
        """Validate order has required fields."""
        return bool(
            order.order_id
            and order.symbol
            and order.side in ["BUY", "SELL"]
            and order.order_type in ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
        )

    def _validate_pricing(self, order: Order) -> bool:
        """Validate pricing logic."""
        if order.order_type in ["LIMIT", "STOP_LIMIT"]:
            if order.price is None or order.price <= 0:
                return False
        if order.order_type in ["STOP", "STOP_LIMIT"]:
            if order.stop_price is None or order.stop_price <= 0:
                return False
        return True

    def _validate_quantity(self, order: Order) -> bool:
        """Validate order quantity."""
        return order.quantity > 0 and order.quantity <= 1000000
