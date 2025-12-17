"""
RouteOrderProcessor for trading platform.

Handles routing of Order entities to execution venues and creates
audit trail events for order routing activities.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.order.version_1.order import Order
from application.entity.audit_event.version_1.audit_event import AuditEvent
from services.services import get_entity_service


class RouteOrderProcessor(CyodaProcessor):
    """
    Processor for Order that handles order routing.

    Simulates routing orders to execution venues and creates AuditEvent
    entities to track routing decisions and execution venue selection.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RouteOrderProcessor",
            description="Routes Order entities to execution venues and creates audit events",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Order entity and route to execution venue.

        Args:
            entity: The Order entity to route
            **kwargs: Additional processing parameters

        Returns:
            The processed Order entity with routing information
        """
        try:
            self.logger.info(
                f"Processing Order {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Order for type-safe operations
            order = cast_entity(entity, Order)

            # Determine execution venue based on order type and instrument
            execution_venue = self._determine_execution_venue(order)

            # Update order with routing information
            order.execution_venue = execution_venue
            order.routed_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            order.routing_status = "ROUTED"

            # Create audit event for order routing
            await self._create_routing_audit_event(order, execution_venue)

            self.logger.info(
                f"Order {order.technical_id} routed to {execution_venue}"
            )

            return order

        except Exception as e:
            self.logger.error(
                f"Error processing Order {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _determine_execution_venue(self, order: Order) -> str:
        """
        Determine the appropriate execution venue for the order.

        Args:
            order: The Order entity to route

        Returns:
            Execution venue identifier
        """
        # Simplified routing logic - in production this would be more sophisticated
        # based on factors like liquidity, fees, order type, etc.

        if order.order_type == "MARKET":
            venue = "PRIMARY_EXCHANGE"
        elif order.order_type == "LIMIT":
            # Route limit orders to venue with best liquidity
            venue = "ECN_VENUE_A"
        else:
            # Default venue for other order types
            venue = "SMART_ROUTER"

        self.logger.info(
            f"Selected execution venue {venue} for order type {order.order_type}"
        )

        return venue

    async def _create_routing_audit_event(
        self, order: Order, execution_venue: str
    ) -> None:
        """
        Create an AuditEvent for the order routing.

        Args:
            order: The routed Order entity
            execution_venue: The selected execution venue
        """
        try:
            entity_service = get_entity_service()

            current_timestamp = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            # Create AuditEvent
            audit_event = AuditEvent(
                event_type="ORDER_ROUTED",
                entity_type="Order",
                entity_id=order.technical_id or order.entity_id or "unknown",
                actor="RouteOrderProcessor",
                timestamp=current_timestamp,
                details={
                    "order_id": order.technical_id,
                    "instrument_id": order.instrument_id,
                    "order_type": order.order_type,
                    "side": order.side,
                    "quantity": order.quantity,
                    "execution_venue": execution_venue,
                    "account_id": order.account_id,
                },
            )

            # Convert to dict and save
            audit_event_data = audit_event.model_dump(by_alias=True)
            response = await entity_service.save(
                entity=audit_event_data,
                entity_class=AuditEvent.ENTITY_NAME,
                entity_version=str(AuditEvent.ENTITY_VERSION),
            )

            created_event_id = response.metadata.id

            self.logger.info(
                f"Created AuditEvent {created_event_id} for Order {order.technical_id} "
                f"routing to {execution_venue}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to create AuditEvent for Order {order.technical_id}: {str(e)}"
            )
            # Don't fail the order routing if audit event creation fails
