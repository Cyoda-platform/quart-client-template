"""
Order validation criteria for the trading platform.

Validates orders before processing.
"""

import logging
from typing import Any

from common.criterion.base import CyodaCriterion, CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriterion):
    """
    Criterion for validating orders.

    Checks order data integrity and business rules.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates order data and business rules",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate order validation criterion.

        Args:
            entity: The Order entity to validate
            **kwargs: Additional parameters

        Returns:
            True if order is valid, False otherwise
        """
        try:
            self.logger.info(
                f"Validating order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            # Validate required fields
            if not order.order_id:
                self.logger.warning("Order ID is missing")
                return False

            if not order.account_id:
                self.logger.warning("Account ID is missing")
                return False

            if not order.instrument_id:
                self.logger.warning("Instrument ID is missing")
                return False

            # Validate order side
            if order.side not in ["BUY", "SELL"]:
                self.logger.warning(f"Invalid order side: {order.side}")
                return False

            # Validate order type
            if order.type not in ["MARKET", "LIMIT", "STOP"]:
                self.logger.warning(f"Invalid order type: {order.type}")
                return False

            # Validate quantity
            if order.quantity <= 0:
                self.logger.warning("Order quantity must be positive")
                return False

            # Validate price for LIMIT orders
            if order.type == "LIMIT" and (order.price is None or order.price <= 0):
                self.logger.warning("LIMIT orders must have a positive price")
                return False

            self.logger.info(
                f"Order {order.technical_id} validation passed"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Order validation error for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

