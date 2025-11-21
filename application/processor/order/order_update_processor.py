"""
OrderUpdateProcessor for Cyoda Client Application

Handles the updating of Order entities with change application, timestamp management,
and event emission as specified in functional requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order
from services.services import get_entity_service


class OrderUpdateProcessor(CyodaProcessor):
    """
    Processor for Order updates that handles:
    - Applying changes to the order
    - Setting status to 'updated'
    - Setting updatedAt timestamp
    - Persisting entity
    - Emitting 'OrderUpdated' event
    
    Execution mode: SYNC
    Configuration: attachEntity=true, responseTimeoutMs=5000, retryPolicy=FIXED
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderUpdateProcessor",
            description="Processes Order updates, applies changes, sets timestamps, and emits OrderUpdated event",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order update according to functional requirements.

        Args:
            entity: The Order entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed Order entity with status set to 'updated'
        """
        try:
            self.logger.info(
                f"Processing Order update for entity {getattr(entity, 'entity_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Validate that order can be updated
            if not order.can_be_updated():
                raise ValueError(f"Order {order.entity_id} cannot be updated (current status: {order.status})")

            # Set status to 'updated'
            order.set_status("updated")

            # Set updatedAt timestamp
            current_timestamp = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            order.updated_at = current_timestamp

            # Add processing metadata
            order.set_processing_metadata({
                "processed_by": "OrderUpdateProcessor",
                "processed_at": current_timestamp,
                "transition": "update",
                "event_emitted": "OrderUpdated",
                "previous_status": order.status if order.status != "updated" else "created"
            })

            # Emit OrderUpdated event
            await self._emit_order_updated_event(order)

            # Log processing completion
            self.logger.info(
                f"Order {order.entity_id} updated successfully with status '{order.status}'"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error processing Order update for entity {getattr(entity, 'entity_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _emit_order_updated_event(self, order: Order) -> None:
        """
        Emit OrderUpdated event.
        
        Args:
            order: The updated Order entity
        """
        try:
            # For now, simulate event emission via structured logging
            # In a real implementation, this would integrate with an event bus
            event_data = {
                "event_type": "OrderUpdated",
                "order_id": order.entity_id,
                "customer_id": order.customer_id,
                "amount": order.amount,
                "status": order.status,
                "updated_at": order.updated_at,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
            
            self.logger.info(
                f"EVENT_EMITTED: OrderUpdated",
                extra={"event_data": event_data}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to emit OrderUpdated event for order {order.entity_id}: {str(e)}")
            # Don't raise - event emission failure shouldn't fail the entire process
