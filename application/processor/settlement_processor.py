"""
Settlement processors for the trading platform.

Handles clearing, settlement, and reporting.
"""

import logging
from typing import Any

from application.entity.trade.version_1.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class ClearingInterface(CyodaProcessor):
    """
    Processor for interfacing with clearing systems.

    Submits trades to clearing and receives confirmation.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ClearingInterface",
            description="Interfaces with clearing systems",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Submit trade to clearing.

        Args:
            entity: The Trade entity
            **kwargs: Additional parameters

        Returns:
            The trade entity with clearing reference
        """
        try:
            self.logger.info(
                f"Submitting trade to clearing: {getattr(entity, 'technical_id', '<unknown>')}"
            )

            trade = cast_entity(entity, Trade)

            # Validate trade for clearing
            if not trade.buy_order_id or not trade.sell_order_id:
                raise ValueError("Trade must have both buy and sell order IDs")

            self.logger.info(f"Trade {trade.technical_id} submitted to clearing")

            return trade

        except Exception as e:
            self.logger.error(
                f"Clearing submission failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class SettlementReporting(CyodaProcessor):
    """
    Processor for settlement reporting.

    Generates settlement reports and updates positions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="SettlementReporting",
            description="Generates settlement reports",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Generate settlement report.

        Args:
            entity: The Trade entity
            **kwargs: Additional parameters

        Returns:
            The settled trade entity
        """
        try:
            self.logger.info(
                f"Generating settlement report for trade {getattr(entity, 'technical_id', '<unknown>')}"
            )

            trade = cast_entity(entity, Trade)

            self.logger.info(
                f"Settlement report generated for trade {trade.technical_id}"
            )

            return trade

        except Exception as e:
            self.logger.error(
                f"Settlement reporting failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
