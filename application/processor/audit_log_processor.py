import logging
from typing import Any

from application.entity.order import Order
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class AuditLogProcessor(CyodaProcessor):
    """
    Logs trading activities for regulatory compliance and audit trail.
    Records all order lifecycle events and state transitions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="AuditLogProcessor",
            description="Logs trading activities for audit trail",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Log trading activity.

        Args:
            entity: The Order entity to log
            **kwargs: Additional parameters

        Returns:
            The entity after logging
        """
        try:
            order = cast_entity(entity, Order)

            self.logger.info(
                f"AUDIT: Order {order.order_id} - "
                f"Account: {order.account_id}, "
                f"Symbol: {order.symbol}, "
                f"Side: {order.side}, "
                f"Quantity: {order.quantity}, "
                f"Status: {order.status}"
            )
            return order

        except Exception as e:
            self.logger.error(f"Error logging audit trail: {str(e)}")
            raise
