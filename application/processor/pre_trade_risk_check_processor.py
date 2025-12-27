import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order import Order


class PreTradeRiskCheckProcessor(CyodaProcessor):
    """
    Performs pre-trade risk checks before order execution.
    Validates position limits, notional exposure, and margin requirements.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PreTradeRiskCheckProcessor",
            description="Performs pre-trade risk checks",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Perform pre-trade risk checks.

        Args:
            entity: The Order entity to check
            **kwargs: Additional parameters

        Returns:
            The order after risk checks
        """
        try:
            order = cast_entity(entity, Order)

            if order.quantity > 10000:
                self.logger.warning(
                    f"Order {order.order_id} exceeds position limit"
                )
                raise ValueError("Position limit exceeded")

            if order.total_cost > 1000000:
                self.logger.warning(
                    f"Order {order.order_id} exceeds notional limit"
                )
                raise ValueError("Notional limit exceeded")

            self.logger.info(f"Order {order.order_id} passed risk checks")
            return order

        except Exception as e:
            self.logger.error(f"Error in pre-trade risk check: {str(e)}")
            raise

