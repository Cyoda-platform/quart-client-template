import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.position.version_1.position import Position
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class PositionUpdateProcessor(CyodaProcessor):
    """Updates position P&L and margin calculations."""

    def __init__(self) -> None:
        super().__init__(
            name="PositionUpdateProcessor",
            description="Updates position P&L and margin requirements",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Update position calculations.

        Args:
            entity: The Position entity to process
            **kwargs: Additional processing parameters

        Returns:
            Updated position entity
        """
        try:
            position = cast_entity(entity, Position)

            self.logger.info(f"Updating position {position.entity_id}")

            position.unrealized_pnl = (
                position.current_price - position.average_cost
            ) * position.quantity
            position.margin_required = abs(
                position.quantity * position.average_cost * 0.5
            )
            position.updated_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(f"Position {position.entity_id} updated successfully")
            return position

        except Exception as e:
            self.logger.error(f"Error updating position: {str(e)}")
            raise
