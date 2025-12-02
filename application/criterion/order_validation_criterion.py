"""
OrderValidationCriterion for Real-Time Trading Platform

Validates that Order meets all required business rules before it can
proceed to risk checking stage.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Order that checks all business rules
    before the entity can proceed to risk checking stage.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates Order business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the Order meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Order)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Validate required fields
            if not order.order_id or len(order.order_id.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid order_id"
                )
                return False

            if not order.symbol or len(order.symbol.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid symbol"
                )
                return False

            if order.order_type not in Order.ALLOWED_ORDER_TYPES:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid order_type: {order.order_type}"
                )
                return False

            if order.side not in Order.ALLOWED_SIDES:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid side: {order.side}"
                )
                return False

            if order.quantity <= 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid quantity: {order.quantity}"
                )
                return False

            if not order.portfolio_id or len(order.portfolio_id.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid portfolio_id"
                )
                return False

            if order.time_in_force not in Order.ALLOWED_TIME_IN_FORCE:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid time_in_force: {order.time_in_force}"
                )
                return False

            # Validate price requirements based on order type
            if order.order_type in ["LIMIT", "STOP_LIMIT"]:
                if order.price is None or order.price <= 0:
                    self.logger.warning(
                        f"Order {order.technical_id} {order.order_type} requires valid price"
                    )
                    return False

            if order.order_type in ["STOP", "STOP_LIMIT"]:
                if order.stop_price is None or order.stop_price <= 0:
                    self.logger.warning(
                        f"Order {order.technical_id} {order.order_type} requires valid stop_price"
                    )
                    return False

            # Validate filled quantity doesn't exceed total quantity
            if order.filled_quantity > order.quantity:
                self.logger.warning(
                    f"Order {order.technical_id} filled_quantity exceeds quantity"
                )
                return False

            # Validate business logic for stop orders
            if order.order_type == "STOP_LIMIT" and order.price and order.stop_price:
                if order.side == "BUY" and order.price < order.stop_price:
                    self.logger.warning(
                        f"Order {order.technical_id} BUY STOP_LIMIT price must be >= stop_price"
                    )
                    return False
                elif order.side == "SELL" and order.price > order.stop_price:
                    self.logger.warning(
                        f"Order {order.technical_id} SELL STOP_LIMIT price must be <= stop_price"
                    )
                    return False

            # Validate reasonable order size (basic sanity check)
            if order.quantity > 1000000:  # Very large order
                self.logger.warning(
                    f"Order {order.technical_id} has unusually large quantity: {order.quantity}"
                )
                return False

            # Validate reasonable price levels if specified
            if order.price and order.price > 100000:  # Very high price
                self.logger.warning(
                    f"Order {order.technical_id} has unusually high price: {order.price}"
                )
                return False

            self.logger.info(
                f"Order {order.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating Order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
