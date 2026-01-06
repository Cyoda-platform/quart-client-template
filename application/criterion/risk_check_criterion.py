"""
RiskCheckCriterion evaluates order against risk limits.

Checks position limits, notional exposure, and sector concentration.
"""

import logging
from typing import Any

from application.entity.order import Order
from common.criterion.base import CyodaCriterion, CyodaEntity
from common.entity.entity_casting import cast_entity


class RiskCheckCriterion(CyodaCriterion):
    """Evaluates order against risk limits."""

    def __init__(self) -> None:
        super().__init__(
            name="RiskCheckCriterion",
            description="Evaluates order against risk limits and constraints",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """Evaluate if order passes risk checks."""
        try:
            order = cast_entity(entity, Order)

            # Check position limits
            if not self._check_position_limit(order):
                self.logger.warning(f"Order {order.order_id} exceeds position limit")
                return False

            # Check notional exposure
            if not self._check_notional_exposure(order):
                self.logger.warning(f"Order {order.order_id} exceeds notional limit")
                return False

            # Check sector concentration
            if not self._check_sector_concentration(order):
                self.logger.warning(f"Order {order.order_id} violates sector limits")
                return False

            self.logger.info(f"Order {order.order_id} passed risk checks")
            return True

        except Exception as e:
            self.logger.error(f"Error checking order risk: {str(e)}")
            return False

    def _check_position_limit(self, order: Order) -> bool:
        """Check if order respects position limits."""
        max_position = 100000
        return order.quantity <= max_position

    def _check_notional_exposure(self, order: Order) -> bool:
        """Check if order respects notional exposure limits."""
        estimated_price = order.price or 100.0
        notional_value = order.quantity * estimated_price
        max_notional = 10000000
        return notional_value <= max_notional

    def _check_sector_concentration(self, order: Order) -> bool:
        """Check if order respects sector concentration limits."""
        # Simplified check - in production would query portfolio
        return True
