"""
TradeComplianceCriterion for institutional trading platform.

Validates trades for compliance before reporting.
"""

from typing import Any

from application.entity.trade.version_1.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class TradeComplianceCriterion(CyodaCriteriaChecker):
    """
    Compliance validation criterion for trades.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TradeComplianceCriterion",
            description="Validates trades for compliance before reporting",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the trade meets all compliance criteria.

        Args:
            entity: The trade entity to validate
            **kwargs: Additional criteria parameters

        Returns:
            True if the trade is compliant, False otherwise
        """
        try:
            self.logger.info(
                f"Validating trade compliance {getattr(entity, 'technical_id', '<unknown>')}"
            )

            trade = cast_entity(entity, Trade)

            # Validate required fields
            if not trade.trade_id or not trade.symbol or not trade.account_id:
                self.logger.warning("Trade missing required fields")
                return False

            # Validate trade parameters
            if trade.quantity <= 0 or trade.price <= 0:
                self.logger.warning("Trade has invalid quantity or price")
                return False

            # Validate venue
            if not trade.venue:
                self.logger.warning("Trade missing venue information")
                return False

            # Validate counterparty for OTC trades
            if trade.venue == "OTC" and not trade.counterparty:
                self.logger.warning("OTC trade missing counterparty")
                return False

            self.logger.info(f"Trade {trade.trade_id} passed compliance validation")
            return True

        except Exception as e:
            entity_id = getattr(entity, "technical_id", "<unknown>")
            self.logger.error(
                f"Error validating trade compliance {entity_id}: {str(e)}"
            )
            return False
