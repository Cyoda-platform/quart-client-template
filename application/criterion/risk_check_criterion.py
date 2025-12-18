"""
RiskCheckCriterion for trading platform.

Performs pre-trade risk checks against configured limits.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class RiskCheckCriterion(CyodaCriteriaChecker):
    """Performs pre-trade risk checks."""

    def __init__(self) -> None:
        super().__init__(
            name="RiskCheckCriterion",
            description="Performs pre-trade risk validation",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if order passes risk checks.

        Args:
            entity: The order entity to check
            **kwargs: Additional criteria parameters (may include risk limits)

        Returns:
            True if order passes risk checks, False otherwise
        """
        try:
            order = cast_entity(entity, Order)
            self.logger.info(f"Performing risk checks for order {order.client_order_id}")

            # Calculate notional exposure
            notional = order.quantity * (order.price or 0)
            
            # Basic risk checks
            if notional > 10000000:  # $10M limit for demo
                self.logger.warning(f"Order notional {notional} exceeds limit")
                return False

            if order.quantity > 1000000:  # 1M share limit for demo
                self.logger.warning(f"Order quantity {order.quantity} exceeds limit")
                return False

            self.logger.info(f"Order {order.client_order_id} passed risk checks")
            return True

        except Exception as e:
            self.logger.error(f"Error performing risk checks: {str(e)}")
            return False

