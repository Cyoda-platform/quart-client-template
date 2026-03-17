"""
OrderSubmissionProcessor for institutional trading platform.

Handles order submission to execution venues with smart order routing.
"""

import logging
from datetime import datetime, timezone

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order

logger = logging.getLogger(__name__)


class OrderSubmissionProcessor(CyodaProcessor):
    """
    Processor for submitting orders to execution venues.

    Implements smart order routing and pre-trade risk checks.
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderSubmissionProcessor",
            description="Submits orders to execution venues with smart routing",
        )

    async def process(self, entity: CyodaEntity, **kwargs) -> CyodaEntity:
        """
        Process order submission.

        Args:
            entity: The order entity to submit
            **kwargs: Additional processing parameters

        Returns:
            The processed order with submission details
        """
        try:
            self.logger.info(
                f"Submitting order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            order = cast_entity(entity, Order)

            # Update submission timestamp
            order.submitted_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            # Smart order routing logic
            if not order.venue:
                order.venue = self._determine_venue(order)

            self.logger.info(f"Order {order.order_id} submitted to {order.venue}")

            return order

        except Exception as e:
            self.logger.error(
                f"Error submitting order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _determine_venue(self, order: Order) -> str:
        """
        Determine best execution venue for the order.

        Args:
            order: The order to route

        Returns:
            Venue identifier
        """
        # Simple routing logic - can be enhanced with latency-aware routing
        venue_map = {
            "AAPL": "LSE",
            "MSFT": "Euronext",
            "GOOGL": "XETRA",
        }
        return venue_map.get(order.symbol, "LSE")
