import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaCriterion
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriterion):
    """Validates order before opening for execution."""

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates order meets risk and compliance requirements",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate if order is valid for execution.

        Args:
            entity: The Order entity to validate
            **kwargs: Additional context

        Returns:
            True if order is valid, False otherwise
        """
        try:
            order = cast_entity(entity, Order)

            if order.quantity <= 0:
                self.logger.warning(f"Order {order.entity_id}: Invalid quantity")
                return False

            if order.order_type == "LIMIT" and (order.price is None or order.price <= 0):
                self.logger.warning(f"Order {order.entity_id}: LIMIT order missing price")
                return False

            self.logger.info(f"Order {order.entity_id} validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Error validating order: {str(e)}")
            return False

