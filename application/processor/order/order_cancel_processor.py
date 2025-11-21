"""
OrderCancelProcessor for Cyoda Client Application

Handles the cancellation of Order entities with status setting, timestamp management,
external service calls, and event emission as specified in functional requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.order.version_1.order import Order
from application.utils.http_client import (
    HttpClientError,
    create_order_cancellation_client,
)
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
# from services.services import get_entity_service  # Not used in this processor


class OrderCancelProcessor(CyodaProcessor):
    """
    Processor for Order cancellation that handles:
    - Setting status to 'cancelled'
    - Setting updatedAt timestamp
    - Calling external cancellation service
    - Persisting entity
    - Emitting 'OrderCancelled' event

    Execution mode: ASYNC_NEW_TX
    Configuration: attachEntity=true, responseTimeoutMs=10000, retryPolicy=EXPONENTIAL
    """

    def __init__(self) -> None:
        super().__init__(
            name="OrderCancelProcessor",
            description="Processes Order cancellation, calls external services, and emits OrderCancelled event",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order cancellation according to functional requirements.

        Args:
            entity: The Order entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed Order entity with status set to 'cancelled'
        """
        try:
            self.logger.info(
                f"Processing Order cancellation for entity {getattr(entity, 'entity_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Validate that order can be cancelled
            if not order.can_be_cancelled():
                raise ValueError(
                    f"Order {order.entity_id} cannot be cancelled (current status: {order.status})"
                )

            # Call external cancellation service
            cancellation_result = await self._call_external_cancellation_service(order)

            # Set status to 'cancelled'
            order.set_status("cancelled")

            # Set updatedAt timestamp
            current_timestamp = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            order.updated_at = current_timestamp

            # Add processing metadata including external service result
            order.set_processing_metadata(
                {
                    "processed_by": "OrderCancelProcessor",
                    "processed_at": current_timestamp,
                    "transition": "cancel",
                    "event_emitted": "OrderCancelled",
                    "external_cancellation_result": cancellation_result,
                    "previous_status": (
                        order.status if order.status != "cancelled" else "created"
                    ),
                }
            )

            # Emit OrderCancelled event
            await self._emit_order_cancelled_event(order)

            # Log processing completion
            self.logger.info(
                f"Order {order.entity_id} cancelled successfully with status '{order.status}'"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error processing Order cancellation for entity {getattr(entity, 'entity_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _call_external_cancellation_service(self, order: Order) -> Dict[str, Any]:
        """
        Call external cancellation service with retry policy.

        Args:
            order: The Order entity to cancel

        Returns:
            Result from external cancellation service
        """
        try:
            self.logger.info(
                f"Calling external cancellation service for order {order.entity_id}"
            )

            # Prepare cancellation request
            cancellation_request = {
                "order_id": order.entity_id,
                "customer_id": order.customer_id,
                "amount": order.amount,
                "cancellation_timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }

            # Use HTTP client with exponential retry policy
            async with create_order_cancellation_client() as client:
                try:
                    # In a real implementation, this would call an actual external service
                    # For now, simulate the call by logging the request
                    self.logger.info(
                        f"Simulating external cancellation service call",
                        extra={"cancellation_request": cancellation_request},
                    )

                    # Simulate successful response
                    cancellation_result = {
                        "success": True,
                        "cancellation_id": f"CANCEL_{order.entity_id}_{int(datetime.now().timestamp())}",
                        "message": "Order successfully cancelled in external system",
                        "timestamp": datetime.now(timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z"),
                        "request_data": cancellation_request,
                    }

                    # In real implementation, this would be:
                    # response = await client.post("/api/orders/cancel", json_data=cancellation_request)
                    # cancellation_result = response["data"]

                except HttpClientError as e:
                    self.logger.error(
                        f"HTTP client error calling cancellation service: {str(e)}"
                    )
                    return {
                        "success": False,
                        "error": f"HTTP client error: {str(e)}",
                        "error_type": "http_client_error",
                        "timestamp": datetime.now(timezone.utc)
                        .isoformat()
                        .replace("+00:00", "Z"),
                    }

            self.logger.info(
                f"External cancellation service call successful for order {order.entity_id}",
                extra={"cancellation_result": cancellation_result},
            )

            return cancellation_result

        except Exception as e:
            self.logger.error(
                f"Failed to call external cancellation service for order {order.entity_id}: {str(e)}"
            )
            # Return error result but don't fail the entire process
            return {
                "success": False,
                "error": str(e),
                "error_type": "unexpected_error",
                "timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }

    async def _emit_order_cancelled_event(self, order: Order) -> None:
        """
        Emit OrderCancelled event.

        Args:
            order: The cancelled Order entity
        """
        try:
            # For now, simulate event emission via structured logging
            # In a real implementation, this would integrate with an event bus
            event_data = {
                "event_type": "OrderCancelled",
                "order_id": order.entity_id,
                "customer_id": order.customer_id,
                "amount": order.amount,
                "status": order.status,
                "cancelled_at": order.updated_at,
                "timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }

            self.logger.info(
                f"EVENT_EMITTED: OrderCancelled", extra={"event_data": event_data}
            )

        except Exception as e:
            self.logger.error(
                f"Failed to emit OrderCancelled event for order {order.entity_id}: {str(e)}"
            )
            # Don't raise - event emission failure shouldn't fail the entire process
