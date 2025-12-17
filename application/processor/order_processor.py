import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from application.entity.order.version_1.order import Order
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class OrderProcessor(CyodaProcessor):
    """
    Processor for Order that handles order submission and routing logic.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderProcessor",
            description="Processes Order instances and routes to execution venues",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order for submission.

        Args:
            entity: The Order to process
            **kwargs: Additional processing parameters

        Returns:
            The processed order with submission details
        """
        try:
            self.logger.info(
                f"Processing Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            if not order.order_id:
                order.order_id = f"ORD_{uuid.uuid4().hex[:12].upper()}"

            order.submitted_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            order.status = "SUBMITTED"

            self.logger.info(f"Order {order.order_id} submitted successfully")

            return order

        except Exception as e:
            self.logger.error(
                f"Error processing order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
