"""
Trade validation criteria for the trading platform.

Validates trades before matching and settlement.
"""

import logging
from typing import Any

from common.criterion.base import CyodaCriterion, CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.trade.version_1.trade import Trade


class TradeValidationCriterion(CyodaCriterion):
    """
    Criterion for validating trades.

    Checks trade data integrity and business rules.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TradeValidationCriterion",
            description="Validates trade data and business rules",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate trade validation criterion.

        Args:
            entity: The Trade entity to validate
            **kwargs: Additional parameters

        Returns:
            True if trade is valid, False otherwise
        """
        try:
            self.logger.info(
                f"Validating trade {getattr(entity, 'technical_id', '<unknown>')}"
            )

            trade = cast_entity(entity, Trade)

            # Validate required fields
            if not trade.trade_id:
                self.logger.warning("Trade ID is missing")
                return False

            if not trade.buy_order_id:
                self.logger.warning("Buy order ID is missing")
                return False

            if not trade.sell_order_id:
                self.logger.warning("Sell order ID is missing")
                return False

            if not trade.instrument_id:
                self.logger.warning("Instrument ID is missing")
                return False

            # Validate quantity
            if trade.quantity <= 0:
                self.logger.warning("Trade quantity must be positive")
                return False

            # Validate price
            if trade.price <= 0:
                self.logger.warning("Trade price must be positive")
                return False

            self.logger.info(
                f"Trade {trade.technical_id} validation passed"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Trade validation error for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

