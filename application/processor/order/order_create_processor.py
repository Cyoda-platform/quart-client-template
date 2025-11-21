"""
OrderCreateProcessor for Cyoda Client Application

Handles the creation of Order entities with status setting, timestamp management,
and event emission as specified in functional requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order
from services.services import get_entity_service


class OrderCreateProcessor(CyodaProcessor):
    """
    Processor for Order creation that handles:
    - Setting status to 'created'
    - Setting createdAt timestamp
    - Persisting entity
    - Emitting 'OrderCreated' event
    
    Execution mode: SYNC
    Configuration: attachEntity=true, responseTimeoutMs=5000, retryPolicy=FIXED
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderCreateProcessor",
            description="Processes Order creation, sets status and timestamps, and emits OrderCreated event",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order creation according to functional requirements.

        Args:
            entity: The Order entity to process (must be in initial state)
            **kwargs: Additional processing parameters

        Returns:
            The processed Order entity with status set to 'created'
        """
        try:
            self.logger.info(
                f"Processing Order creation for entity {getattr(entity, 'entity_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Set status to 'created'
            order.set_status("created")

            # Set createdAt timestamp (should already be set, but ensure it's current)
            current_timestamp = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            order.created_at = current_timestamp

            # Add processing metadata
            order.set_processing_metadata({
                "processed_by": "OrderCreateProcessor",
                "processed_at": current_timestamp,
                "transition": "create",
                "event_emitted": "OrderCreated"
            })

            # Emit OrderCreated event (simulated via logging for now)
            await self._emit_order_created_event(order)

            # Log processing completion
            self.logger.info(
                f"Order {order.entity_id} created successfully with status '{order.status}'"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error processing Order creation for entity {getattr(entity, 'entity_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _emit_order_created_event(self, order: Order) -> None:
        """
        Emit OrderCreated event.
        
        Args:
            order: The created Order entity
        """
        try:
            # For now, simulate event emission via structured logging
            # In a real implementation, this would integrate with an event bus
            event_data = {
                "event_type": "OrderCreated",
                "order_id": order.entity_id,
                "customer_id": order.customer_id,
                "amount": order.amount,
                "status": order.status,
                "created_at": order.created_at,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
            
            self.logger.info(
                f"EVENT_EMITTED: OrderCreated",
                extra={"event_data": event_data}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to emit OrderCreated event for order {order.entity_id}: {str(e)}")
            # Don't raise - event emission failure shouldn't fail the entire process
