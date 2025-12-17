import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.position.version_1.position import Position
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class PositionProcessor(CyodaProcessor):
    """
    Processor for Position that handles position activation and P&L calculation.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PositionProcessor",
            description="Processes Position instances and calculates P&L",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Position for activation.

        Args:
            entity: The Position to process
            **kwargs: Additional processing parameters

        Returns:
            The processed position with calculated values
        """
        try:
            self.logger.info(
                f"Processing Position {getattr(entity, 'technical_id', '<unknown>')}"
            )

            position = cast_entity(entity, Position)

            if position.quantity and position.average_price and position.current_price:
                position.market_value = position.quantity * position.current_price
                position.unrealized_pnl = position.quantity * (
                    position.current_price - position.average_price
                )

            position.status = "ACTIVE"

            self.logger.info(f"Position {position.instrument} activated successfully")

            return position

        except Exception as e:
            self.logger.error(
                f"Error processing position {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
