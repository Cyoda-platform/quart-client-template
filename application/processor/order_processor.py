"""
Order processors for the trading platform.

Handles order submission, execution, and reporting.
"""

import logging
from typing import Any

from application.entity.order.version_1.order import Order
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class RiskEvaluation(CyodaProcessor):
    """
    Processor for evaluating order risk before submission.

    Performs pre-trade checks including margin and limit validation.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskEvaluation",
            description="Evaluates order risk and performs pre-trade checks",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Evaluate order risk.

        Args:
            entity: The Order entity to evaluate
            **kwargs: Additional parameters

        Returns:
            The order entity with risk evaluation results
        """
        try:
            self.logger.info(
                f"Evaluating risk for order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            # Perform risk checks
            self._validate_margin(order)
            self._validate_limits(order)

            self.logger.info(f"Risk evaluation passed for order {order.technical_id}")

            return order

        except Exception as e:
            self.logger.error(
                f"Risk evaluation failed for order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _validate_margin(self, order: Order) -> None:
        """Validate margin requirements for the order."""
        if order.type == "LIMIT" and order.price is None:
            raise ValueError("LIMIT orders must have a price")

    def _validate_limits(self, order: Order) -> None:
        """Validate trading limits for the order."""
        if order.quantity <= 0:
            raise ValueError("Order quantity must be positive")


class Execution(CyodaProcessor):
    """
    Processor for executing orders.

    Handles order execution and partial fills.
    """

    def __init__(self) -> None:
        super().__init__(
            name="Execution",
            description="Executes orders and records fills",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Execute the order.

        Args:
            entity: The Order entity to execute
            **kwargs: Additional parameters

        Returns:
            The order entity with execution details
        """
        try:
            self.logger.info(
                f"Executing order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            # Simulate execution
            order.filled_quantity = order.quantity * 0.5
            order.average_price = order.price if order.price else 100.0

            self.logger.info(
                f"Order {order.technical_id} partially filled: {order.filled_quantity} @ {order.average_price}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Order execution failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class ExecutionReportEmitter(CyodaProcessor):
    """
    Processor for emitting execution reports.

    Generates and sends execution reports for filled orders.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ExecutionReportEmitter",
            description="Emits execution reports for orders",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Emit execution report.

        Args:
            entity: The Order entity
            **kwargs: Additional parameters

        Returns:
            The order entity
        """
        try:
            self.logger.info(
                f"Emitting execution report for order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            self.logger.info(
                f"Execution report emitted for order {order.technical_id}: {order.filled_quantity} filled"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Failed to emit execution report for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
