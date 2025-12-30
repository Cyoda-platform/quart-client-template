"""
OrderValidationCriterion for institutional trading platform.

Validates orders before routing.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order import Order


class OrderValidationCriterion(CyodaCriteriaChecker):
    """
    Validates that an Order meets all required business rules
    before it can proceed to routing.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates orders before routing",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the order is valid for routing.

        Args:
            entity: The Order entity to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            order = cast_entity(entity, Order)

            # Validate required fields
            if not order.account_id or not order.instrument_id:
                return False

            # Validate order type
            valid_types = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT", "FOK", "IOC"}
            if order.order_type not in valid_types:
                return False

            # Validate side
            if order.side not in {"BUY", "SELL"}:
                return False

            # Validate quantity
            if order.quantity <= 0:
                return False

            # Validate price for limit orders
            if order.order_type in {"LIMIT", "STOP_LIMIT"} and order.price is None:
                return False

            return True

        except Exception:
            return False

