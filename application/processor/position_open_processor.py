"""
PositionOpenProcessor for position opening.

Initializes new positions from order executions.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.position.version_1.position import Position
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class PositionOpenProcessor(CyodaProcessor):
    """Opens new positions from order executions."""

    def __init__(self) -> None:
        super().__init__(name="PositionOpenProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Open a new position.

        Args:
            entity: The position entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed position entity
        """
        try:
            self.logger.info(
                f"Opening position {getattr(entity, 'technical_id', '<unknown>')}"
            )

            position = cast_entity(entity, Position)

            # Validate position data
            if position.quantity == 0:
                raise ValueError("Position quantity cannot be zero")

            if position.avg_cost <= 0:
                raise ValueError("Average cost must be positive")

            position.updated_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(
                f"Position {position.technical_id} opened: {position.quantity} shares"
            )
            return position

        except Exception as e:
            self.logger.error(f"Error opening position: {str(e)}")
            raise
