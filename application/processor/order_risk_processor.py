"""
OrderRiskProcessor for Trading Platform

Handles risk validation for orders including position limits,
exposure checks, and risk threshold monitoring.
"""

import logging
from typing import Any
from decimal import Decimal

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order


class OrderRiskProcessor(CyodaProcessor):
    """
    Processor for Order risk validation that checks position limits,
    exposure thresholds, and other risk controls.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderRiskProcessor",
            description="Validates orders against risk limits and exposure thresholds",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order risk validation.

        Args:
            entity: The Order to validate (must be in 'validated' state)
            **kwargs: Additional processing parameters

        Returns:
            The order with risk validation results
        """
        try:
            self.logger.info(
                f"Risk checking Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Perform risk checks
            risk_results = await self._perform_risk_checks(order)
            
            # Update order with risk check results
            order.risk_checked = True
            order.risk_check_time = risk_results["check_time"]
            order.risk_warnings = risk_results["warnings"]
            
            # Set risk flags
            if risk_results["has_violations"]:
                order.risk_violation = True
                order.rejection_reason = risk_results["violation_reason"]
                self.logger.warning(
                    f"Order {order.technical_id} has risk violations: {order.rejection_reason}"
                )
            else:
                order.risk_violation = False

            self.logger.info(
                f"Order {order.technical_id} risk check completed - "
                f"Violations: {order.risk_violation}, Warnings: {len(order.risk_warnings or [])}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error in risk check for order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _perform_risk_checks(self, order: Order) -> dict:
        """
        Perform comprehensive risk checks on the order.

        Args:
            order: The Order to check

        Returns:
            Dictionary containing risk check results
        """
        from datetime import datetime, timezone
        
        warnings = []
        violations = []
        
        # Check order size limits
        max_order_size = self._get_max_order_size(order.symbol)
        if order.quantity > max_order_size:
            violations.append(f"Order quantity {order.quantity} exceeds maximum {max_order_size}")

        # Check order value limits
        estimated_value = order.quantity * (order.price or Decimal("100"))
        max_order_value = Decimal("1000000")  # $1M limit
        if estimated_value > max_order_value:
            violations.append(f"Order value {estimated_value} exceeds maximum {max_order_value}")

        # Check position concentration
        concentration_limit = await self._check_concentration_limit(order)
        if concentration_limit["exceeded"]:
            violations.append(concentration_limit["message"])

        # Check leverage limits
        leverage_check = await self._check_leverage_limits(order)
        if leverage_check["exceeded"]:
            violations.append(leverage_check["message"])

        # Warning checks (don't block order)
        if estimated_value > Decimal("500000"):  # $500K warning threshold
            warnings.append("Large order value - requires additional monitoring")

        if order.order_type == "MARKET" and order.quantity > 10000:
            warnings.append("Large market order may cause significant market impact")

        return {
            "check_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "warnings": warnings,
            "violations": violations,
            "has_violations": len(violations) > 0,
            "violation_reason": "; ".join(violations) if violations else None,
        }

    def _get_max_order_size(self, symbol: str) -> Decimal:
        """
        Get maximum order size for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Maximum allowed order size
        """
        # Symbol-specific limits (in real system, from configuration)
        symbol_limits = {
            "AAPL": Decimal("50000"),
            "MSFT": Decimal("40000"),
            "GOOGL": Decimal("10000"),
            "TSLA": Decimal("30000"),
        }
        
        return symbol_limits.get(symbol, Decimal("25000"))  # Default limit

    async def _check_concentration_limit(self, order: Order) -> dict:
        """
        Check if order would exceed concentration limits.

        Args:
            order: The order to check

        Returns:
            Dictionary with concentration check results
        """
        # Simulate concentration check
        # In real system, would query current positions and calculate exposure
        
        max_concentration = Decimal("0.20")  # 20% max concentration per symbol
        current_concentration = Decimal("0.15")  # Simulated current concentration
        
        order_value = order.quantity * (order.price or Decimal("100"))
        portfolio_value = Decimal("10000000")  # $10M portfolio
        
        new_concentration = current_concentration + (order_value / portfolio_value)
        
        if new_concentration > max_concentration:
            return {
                "exceeded": True,
                "message": f"Order would exceed concentration limit: {new_concentration:.2%} > {max_concentration:.2%}"
            }
        
        return {"exceeded": False, "message": None}

    async def _check_leverage_limits(self, order: Order) -> dict:
        """
        Check if order would exceed leverage limits.

        Args:
            order: The order to check

        Returns:
            Dictionary with leverage check results
        """
        # Simulate leverage check
        max_leverage = Decimal("4.0")  # 4:1 leverage limit
        current_leverage = Decimal("2.5")  # Simulated current leverage
        
        # For simplicity, assume order doesn't significantly change leverage
        if current_leverage > max_leverage:
            return {
                "exceeded": True,
                "message": f"Current leverage {current_leverage} exceeds limit {max_leverage}"
            }
        
        return {"exceeded": False, "message": None}
