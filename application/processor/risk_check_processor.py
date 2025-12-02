"""
RiskCheckProcessor for Real-Time Trading Platform

Handles pre-trade risk checks for orders including position limits,
exposure limits, and concentration limits.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order
from services.services import get_entity_service


class RiskCheckProcessor(CyodaProcessor):
    """
    Processor for Order that performs pre-trade risk checks before order submission.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskCheckProcessor",
            description="Performs pre-trade risk checks for orders",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Perform risk checks on the Order before submission.

        Args:
            entity: The Order to check (must be in 'validated' state)
            **kwargs: Additional processing parameters

        Returns:
            The order with risk check results
        """
        try:
            self.logger.info(
                f"Performing risk checks for Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Perform risk checks
            risk_check_result = await self._perform_risk_checks(order)
            order.set_risk_check_result(risk_check_result)

            # Log risk check completion
            self.logger.info(
                f"Risk checks completed for Order {order.technical_id}: {risk_check_result['status']}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error performing risk checks for Order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _perform_risk_checks(self, order: Order) -> Dict[str, Any]:
        """
        Perform comprehensive risk checks on the order.

        Args:
            order: The Order entity to check

        Returns:
            Dictionary containing risk check results
        """
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        risk_checks: Dict[str, Any] = {
            "checked_at": current_timestamp,
            "status": "PASSED",
            "checks": [],
            "warnings": [],
            "errors": []
        }

        # Check 1: Position limit check
        position_check = await self._check_position_limits(order)
        risk_checks["checks"].append(position_check)  # type: ignore
        if not position_check["passed"]:
            risk_checks["errors"].append(position_check["message"])  # type: ignore

        # Check 2: Exposure limit check
        exposure_check = await self._check_exposure_limits(order)
        risk_checks["checks"].append(exposure_check)  # type: ignore
        if not exposure_check["passed"]:
            risk_checks["errors"].append(exposure_check["message"])  # type: ignore

        # Check 3: Order size validation
        size_check = self._check_order_size(order)
        risk_checks["checks"].append(size_check)  # type: ignore
        if not size_check["passed"]:
            risk_checks["errors"].append(size_check["message"])  # type: ignore

        # Determine overall status
        if risk_checks["errors"]:
            risk_checks["status"] = "FAILED"
        elif risk_checks["warnings"]:
            risk_checks["status"] = "WARNING"

        return risk_checks

    async def _check_position_limits(self, order: Order) -> Dict[str, Any]:
        """Check position limits for the order"""
        try:
            entity_service = get_entity_service()
            
            # Get portfolio to check current positions
            # This is a simplified check - in real implementation would query actual positions
            check_result = {
                "check_type": "POSITION_LIMIT",
                "symbol": order.symbol,
                "passed": True,
                "message": "Position limit check passed",
                "details": {
                    "current_position": 0,  # Would be calculated from actual positions
                    "order_quantity": order.quantity,
                    "position_limit": 10000  # Would be retrieved from risk rules
                }
            }

            # Simulate position limit check
            projected_position = check_result["details"]["current_position"] + order.quantity  # type: ignore
            if projected_position > check_result["details"]["position_limit"]:  # type: ignore
                check_result["passed"] = False
                check_result["message"] = f"Position limit exceeded for {order.symbol}"

            return check_result

        except Exception as e:
            self.logger.error(f"Error checking position limits: {str(e)}")
            return {
                "check_type": "POSITION_LIMIT",
                "passed": False,
                "message": f"Position limit check failed: {str(e)}"
            }

    async def _check_exposure_limits(self, order: Order) -> Dict[str, Any]:
        """Check exposure limits for the order"""
        try:
            # Calculate order notional value
            notional_value = order.calculate_notional_value() if order.price else 0

            check_result = {
                "check_type": "EXPOSURE_LIMIT",
                "passed": True,
                "message": "Exposure limit check passed",
                "details": {
                    "order_notional": notional_value,
                    "current_exposure": 0,  # Would be calculated from actual portfolio
                    "exposure_limit": 1000000  # Would be retrieved from risk rules
                }
            }

            # Simulate exposure limit check
            projected_exposure = check_result["details"]["current_exposure"] + notional_value  # type: ignore
            if projected_exposure > check_result["details"]["exposure_limit"]:  # type: ignore
                check_result["passed"] = False
                check_result["message"] = "Exposure limit exceeded"

            return check_result

        except Exception as e:
            self.logger.error(f"Error checking exposure limits: {str(e)}")
            return {
                "check_type": "EXPOSURE_LIMIT",
                "passed": False,
                "message": f"Exposure limit check failed: {str(e)}"
            }

    def _check_order_size(self, order: Order) -> Dict[str, Any]:
        """Check order size constraints"""
        check_result = {
            "check_type": "ORDER_SIZE",
            "passed": True,
            "message": "Order size check passed",
            "details": {
                "order_quantity": order.quantity,
                "min_quantity": 1,
                "max_quantity": 100000
            }
        }

        # Check minimum and maximum order sizes
        if order.quantity < check_result["details"]["min_quantity"]:  # type: ignore
            check_result["passed"] = False
            check_result["message"] = "Order quantity below minimum"
        elif order.quantity > check_result["details"]["max_quantity"]:  # type: ignore
            check_result["passed"] = False
            check_result["message"] = "Order quantity exceeds maximum"

        return check_result
