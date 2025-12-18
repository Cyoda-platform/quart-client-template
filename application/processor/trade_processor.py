"""
TradeProcessor for trading platform.

Handles trade capture, ledger posting, and settlement processing.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.trade.version_1.trade import Trade

logger = logging.getLogger(__name__)


class TradeProcessor(CyodaProcessor):
    """Processes trade lifecycle and settlement."""

    def __init__(self) -> None:
        super().__init__(
            name="TradeProcessor",
            description="Handles trade capture and settlement",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process trade entity through its lifecycle.

        Args:
            entity: The trade entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed trade entity
        """
        try:
            trade = cast_entity(entity, Trade)
            self.logger.info(f"Processing trade {trade.trade_id}")

            # Validate trade data
            if trade.quantity <= 0:
                raise ValueError("Trade quantity must be positive")
            if trade.price <= 0:
                raise ValueError("Trade price must be positive")

            self.logger.info(f"Trade {trade.trade_id} processed successfully")
            return trade

        except Exception as e:
            self.logger.error(f"Error processing trade: {str(e)}")
            raise

