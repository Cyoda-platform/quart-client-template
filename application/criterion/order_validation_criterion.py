"""
OrderValidationCriterion for Trading Platform

Validates that an Order meets all required business rules before it can
proceed to risk checking and execution stages.
"""

from typing import Any
from decimal import Decimal

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.order.version_1.order import Order


class OrderValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Order that checks all business rules
    before the order can proceed to risk checking stage.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderValidationCriterion",
            description="Validates Order business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the order meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Order)
            **kwargs: Additional criteria parameters

        Returns:
            True if the order meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Validate required fields
            if not order.order_id or len(order.order_id.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid order_id"
                )
                return False

            if not order.client_id or len(order.client_id.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid client_id"
                )
                return False

            if not order.symbol or len(order.symbol.strip()) == 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid symbol"
                )
                return False

            # Validate order side
            if order.side not in ["BUY", "SELL"]:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid side: {order.side}"
                )
                return False

            # Validate order type
            if order.order_type not in ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid order_type: {order.order_type}"
                )
                return False

            # Validate quantity
            if order.quantity <= 0:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid quantity: {order.quantity}"
                )
                return False

            # Validate price for limit orders
            if order.order_type in ["LIMIT", "STOP_LIMIT"]:
                if not order.price or order.price <= 0:
                    self.logger.warning(
                        f"Order {order.technical_id} limit order requires valid price"
                    )
                    return False

            # Validate stop price for stop orders
            if order.order_type in ["STOP", "STOP_LIMIT"]:
                if not order.stop_price or order.stop_price <= 0:
                    self.logger.warning(
                        f"Order {order.technical_id} stop order requires valid stop_price"
                    )
                    return False

            # Validate time in force
            if order.time_in_force not in ["DAY", "GTC", "IOC", "FOK"]:
                self.logger.warning(
                    f"Order {order.technical_id} has invalid time_in_force: {order.time_in_force}"
                )
                return False

            # Business logic validations
            if order.order_type == "MARKET" and order.time_in_force == "GTC":
                self.logger.warning(
                    f"Order {order.technical_id} market orders cannot be GTC"
                )
                return False

            # Validate minimum order size
            min_order_size = self._get_min_order_size(order.symbol)
            if order.quantity < min_order_size:
                self.logger.warning(
                    f"Order {order.technical_id} quantity {order.quantity} below minimum {min_order_size}"
                )
                return False

            # Validate maximum order size
            max_order_size = self._get_max_order_size(order.symbol)
            if order.quantity > max_order_size:
                self.logger.warning(
                    f"Order {order.technical_id} quantity {order.quantity} exceeds maximum {max_order_size}"
                )
                return False

            # Validate price reasonableness for limit orders
            if order.order_type in ["LIMIT", "STOP_LIMIT"] and order.price:
                if not self._is_price_reasonable(order.symbol, order.price):
                    self.logger.warning(
                        f"Order {order.technical_id} price {order.price} is not reasonable for {order.symbol}"
                    )
                    return False

            self.logger.info(
                f"Order {order.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

    def _get_min_order_size(self, symbol: str) -> Decimal:
        """Get minimum order size for a symbol."""
        # Symbol-specific minimums (in real system, from configuration)
        symbol_minimums = {
            "AAPL": Decimal("1"),
            "MSFT": Decimal("1"),
            "GOOGL": Decimal("1"),
            "TSLA": Decimal("1"),
        }
        return symbol_minimums.get(symbol, Decimal("1"))  # Default minimum

    def _get_max_order_size(self, symbol: str) -> Decimal:
        """Get maximum order size for a symbol."""
        # Symbol-specific maximums (in real system, from configuration)
        symbol_maximums = {
            "AAPL": Decimal("100000"),
            "MSFT": Decimal("100000"),
            "GOOGL": Decimal("50000"),
            "TSLA": Decimal("75000"),
        }
        return symbol_maximums.get(symbol, Decimal("50000"))  # Default maximum

    def _is_price_reasonable(self, symbol: str, price: Decimal) -> bool:
        """Check if price is reasonable for the symbol."""
        # Get reference prices (in real system, from market data)
        reference_prices = {
            "AAPL": Decimal("150"),
            "MSFT": Decimal("300"),
            "GOOGL": Decimal("2500"),
            "TSLA": Decimal("200"),
        }
        
        reference_price = reference_prices.get(symbol, Decimal("100"))
        
        # Allow +/- 20% from reference price
        min_price = reference_price * Decimal("0.8")
        max_price = reference_price * Decimal("1.2")
        
        return min_price <= price <= max_price
