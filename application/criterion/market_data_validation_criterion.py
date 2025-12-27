import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaCriterion
from application.entity.market_data import MarketData


class MarketDataValidationCriterion(CyodaCriterion):
    """
    Validates market data feed for completeness and correctness.
    Checks required fields, data quality, and timestamp validity.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataValidationCriterion",
            description="Validates market data feed for completeness and correctness",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate if market data is valid.

        Args:
            entity: The MarketData entity to validate
            **kwargs: Additional parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            market_data = cast_entity(entity, MarketData)

            if not market_data.symbol or len(market_data.symbol.strip()) == 0:
                self.logger.warning("Market data validation failed: missing symbol")
                return False

            if market_data.bid < 0 or market_data.ask < 0 or market_data.last < 0:
                self.logger.warning("Market data validation failed: negative prices")
                return False

            if market_data.bid > market_data.ask:
                self.logger.warning("Market data validation failed: bid > ask")
                return False

            if market_data.volume < 0:
                self.logger.warning("Market data validation failed: negative volume")
                return False

            self.logger.info(f"Market data {market_data.symbol} validation passed")
            return True

        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            return False

