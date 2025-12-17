"""
InitializePositionProcessor for trading platform.

Handles initialization of new Position entities by setting default P&L
values and preparing positions for tracking.
"""

import logging
from typing import Any

from application.entity.position.version_1.position import Position
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class InitializePositionProcessor(CyodaProcessor):
    """
    Processor for Position that handles initialization.

    Initializes P&L fields to 0.0 and sets up the position entity
    for tracking and management through the system.
    """

    def __init__(self) -> None:
        super().__init__(
            name="InitializePositionProcessor",
            description="Initializes Position entities with default P&L values",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Position entity and initialize P&L fields.

        Args:
            entity: The Position entity to initialize
            **kwargs: Additional processing parameters

        Returns:
            The initialized Position entity
        """
        try:
            self.logger.info(
                f"Processing Position {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Position for type-safe operations
            position = cast_entity(entity, Position)

            # Initialize P&L fields to 0.0 if not already set
            if position.unrealized_pnl is None:
                position.unrealized_pnl = 0.0

            if position.realized_pnl is None:
                position.realized_pnl = 0.0

            # Initialize current_price if not set
            if position.current_price is None:
                position.current_price = position.average_price

            self.logger.info(
                f"Position {position.technical_id} initialized - "
                f"account: {position.account_id}, instrument: {position.instrument_id}, "
                f"quantity: {position.quantity}, avg_price: {position.average_price}, "
                f"unrealized_pnl: {position.unrealized_pnl}, realized_pnl: {position.realized_pnl}"
            )

            return position

        except Exception as e:
            error_id = getattr(entity, 'technical_id', '<unknown>')
            self.logger.error(
                f"Error processing Position {error_id}: {str(e)}"
            )
            raise
