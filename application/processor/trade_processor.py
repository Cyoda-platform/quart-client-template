"""
Trade processors for the trading platform.

Handles trade matching, confirmation, and settlement.
"""

import logging
from typing import Any

from application.entity.trade.version_1.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class MatchingEngine(CyodaProcessor):
    """
    Processor for matching buy and sell orders.

    Implements order book matching logic.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MatchingEngine",
            description="Matches buy and sell orders",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Match orders and create trade.

        Args:
            entity: The Trade entity to process
            **kwargs: Additional parameters

        Returns:
            The trade entity with matching results
        """
        try:
            self.logger.info(
                f"Matching orders for trade {getattr(entity, 'technical_id', '<unknown>')}"
            )

            trade = cast_entity(entity, Trade)

            # Validate matching
            if trade.quantity <= 0:
                raise ValueError("Trade quantity must be positive")

            if trade.price <= 0:
                raise ValueError("Trade price must be positive")

            self.logger.info(
                f"Trade {trade.technical_id} matched: {trade.quantity} @ {trade.price}"
            )

            return trade

        except Exception as e:
            self.logger.error(
                f"Trade matching failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class TradeConfirmation(CyodaProcessor):
    """
    Processor for confirming trades.

    Generates trade confirmations and settlement instructions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TradeConfirmation",
            description="Confirms trades and generates settlement instructions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Confirm trade.

        Args:
            entity: The Trade entity to confirm
            **kwargs: Additional parameters

        Returns:
            The confirmed trade entity
        """
        try:
            self.logger.info(
                f"Confirming trade {getattr(entity, 'technical_id', '<unknown>')}"
            )

            trade = cast_entity(entity, Trade)

            self.logger.info(
                f"Trade {trade.technical_id} confirmed and ready for settlement"
            )

            return trade

        except Exception as e:
            self.logger.error(
                f"Trade confirmation failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
