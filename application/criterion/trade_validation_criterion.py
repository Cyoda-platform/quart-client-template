"""
TradeValidationCriterion for trading platform.

Validates trade data before ledger posting.
"""

from typing import Any

from application.entity.trade.version_1.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class TradeValidationCriterion(CyodaCriteriaChecker):
    """Validates trade data before ledger posting."""

    def __init__(self) -> None:
        super().__init__(
            name="TradeValidationCriterion",
            description="Validates trade data and calculations",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if trade meets validation criteria.

        Args:
            entity: The trade entity to validate
            **kwargs: Additional criteria parameters

        Returns:
            True if trade is valid, False otherwise
        """
        try:
            trade = cast_entity(entity, Trade)
            self.logger.info(f"Validating trade {trade.trade_id}")

            # Validate required fields
            if not trade.symbol or len(trade.symbol) == 0:
                self.logger.warning("Trade missing symbol")
                return False

            if trade.quantity <= 0:
                self.logger.warning("Trade quantity must be positive")
                return False

            if trade.price <= 0:
                self.logger.warning("Trade price must be positive")
                return False

            if trade.side not in ("BUY", "SELL"):
                self.logger.warning(f"Invalid trade side: {trade.side}")
                return False

            # Validate amounts
            expected_gross = trade.quantity * trade.price
            if abs(trade.gross_amount - expected_gross) > 0.01:
                self.logger.warning(
                    f"Trade gross amount mismatch: {trade.gross_amount} vs {expected_gross}"
                )
                return False

            expected_net = trade.gross_amount - trade.commission - trade.fees
            if abs(trade.net_amount - expected_net) > 0.01:
                self.logger.warning(
                    f"Trade net amount mismatch: {trade.net_amount} vs {expected_net}"
                )
                return False

            self.logger.info(f"Trade {trade.trade_id} validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Error validating trade: {str(e)}")
            return False
