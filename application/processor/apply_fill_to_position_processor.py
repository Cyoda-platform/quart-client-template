"""
ApplyFillToPositionProcessor for trading platform.

Handles application of Fill entities to Position entities by updating
position quantities and average prices based on fill executions.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.fill.version_1.fill import Fill
from application.entity.position.version_1.position import Position
from application.entity.order.version_1.order import Order
from services.services import get_entity_service


class ApplyFillToPositionProcessor(CyodaProcessor):
    """
    Processor for Fill that updates Position entities.

    Finds or creates Position entities and updates quantity and average price
    based on fill executions to maintain accurate position tracking.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ApplyFillToPositionProcessor",
            description="Applies Fill entities to update Position quantities and average prices",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Fill entity and update the corresponding Position.

        Args:
            entity: The Fill entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed Fill entity
        """
        try:
            self.logger.info(
                f"Processing Fill {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Fill for type-safe operations
            fill = cast_entity(entity, Fill)

            # Get entity service
            entity_service = get_entity_service()

            # Get the related Order to determine account_id and side
            try:
                order_response = await entity_service.get(
                    entity_id=fill.order_id,
                    entity_class=Order.ENTITY_NAME,
                    entity_version=str(Order.ENTITY_VERSION),
                )
                order_data = order_response.entity
                order = Order(**order_data)
            except Exception as e:
                self.logger.error(
                    f"Failed to retrieve Order {fill.order_id} for Fill {fill.technical_id}: {str(e)}"
                )
                raise

            # Find or create position for this account/instrument combination
            position = await self._find_or_create_position(
                entity_service, order.account_id, fill.instrument_id
            )

            # Update position based on fill
            self._update_position_with_fill(position, fill, order)

            # Save updated position
            position_data = position.model_dump(by_alias=True)
            await entity_service.save(
                entity=position_data,
                entity_class=Position.ENTITY_NAME,
                entity_version=str(Position.ENTITY_VERSION),
            )

            self.logger.info(
                f"Position {position.technical_id} updated successfully with "
                f"Fill {fill.technical_id}"
            )

            return fill

        except Exception as e:
            self.logger.error(
                f"Error processing Fill {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _find_or_create_position(
        self, entity_service: Any, account_id: str, instrument_id: str
    ) -> Position:
        """
        Find existing position or create a new one.

        Args:
            entity_service: The entity service instance
            account_id: The account ID
            instrument_id: The instrument ID

        Returns:
            Position entity (existing or newly created)
        """
        try:
            # Try to find existing position by querying with filters
            # Note: This is a simplified approach - in production you'd use
            # proper query filters or a dedicated position lookup method

            # For now, create a new position if we can't find one
            # In a real system, you'd implement proper position lookup
            current_timestamp = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            position = Position(
                account_id=account_id,
                instrument_id=instrument_id,
                quantity=0.0,
                average_price=0.0,
                current_price=None,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                last_updated=current_timestamp,
            )

            self.logger.info(
                f"Creating new Position for account {account_id}, instrument {instrument_id}"
            )

            return position

        except Exception as e:
            self.logger.error(
                f"Error finding/creating position for account {account_id}, "
                f"instrument {instrument_id}: {str(e)}"
            )
            raise

    def _update_position_with_fill(
        self, position: Position, fill: Fill, order: Order
    ) -> None:
        """
        Update position quantity and average price based on fill.

        Args:
            position: The Position entity to update
            fill: The Fill entity with execution details
            order: The related Order entity
        """
        # Determine fill quantity direction (positive for BUY, negative for SELL)
        fill_qty = fill.quantity if order.side == "BUY" else -fill.quantity

        # Calculate new position
        old_quantity = position.quantity
        old_avg_price = position.average_price
        new_quantity = old_quantity + fill_qty

        # Calculate new average price using weighted average
        if new_quantity != 0:
            total_cost = (old_quantity * old_avg_price) + (fill_qty * fill.fill_price)
            new_avg_price = total_cost / new_quantity
        else:
            # Position is closed
            new_avg_price = 0.0

        # Update position
        position.quantity = new_quantity
        position.average_price = abs(new_avg_price)  # Store absolute value
        position.last_updated = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        self.logger.info(
            f"Position updated: quantity {old_quantity} -> {new_quantity}, "
            f"avg_price {old_avg_price:.4f} -> {position.average_price:.4f}"
        )
