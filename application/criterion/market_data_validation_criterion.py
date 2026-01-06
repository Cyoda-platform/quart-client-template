"""
MarketDataValidationCriterion validates market data feeds.

Checks data quality, consistency, and timeliness.
"""

import logging
from typing import Any

from common.criterion.base import CyodaCriterion, CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.market_data import MarketData


class MarketDataValidationCriterion(CyodaCriterion):
    """Validates market data quality and consistency."""

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataValidationCriterion",
            description="Validates market data quality and consistency",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """Evaluate if market data is valid."""
        try:
            market_data = cast_entity(entity, MarketData)
            
            # Check price consistency
            if not self._check_price_consistency(market_data):
                self.logger.warning(f"Market data for {market_data.symbol} failed price check")
                return False
            
            # Check volume consistency
            if not self._check_volume_consistency(market_data):
                self.logger.warning(f"Market data for {market_data.symbol} failed volume check")
                return False
            
            # Check data freshness
            if not self._check_data_freshness(market_data):
                self.logger.warning(f"Market data for {market_data.symbol} is stale")
                return False
            
            self.logger.info(f"Market data for {market_data.symbol} passed validation")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            return False

    def _check_price_consistency(self, market_data: MarketData) -> bool:
        """Check if prices are consistent."""
        return (
            market_data.bid_price <= market_data.ask_price and
            market_data.low_price <= market_data.high_price and
            market_data.bid_price > 0 and
            market_data.ask_price > 0
        )

    def _check_volume_consistency(self, market_data: MarketData) -> bool:
        """Check if volumes are reasonable."""
        return (
            market_data.bid_size >= 0 and
            market_data.ask_size >= 0 and
            market_data.volume >= 0
        )

    def _check_data_freshness(self, market_data: MarketData) -> bool:
        """Check if data is recent."""
        # Simplified check - in production would compare with current time
        return market_data.timestamp is not None

