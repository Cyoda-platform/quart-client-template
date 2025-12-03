"""
MarketDataProcessor for Trading Platform

Handles market data validation, enrichment, and distribution
for real-time trading operations.
"""

import logging
from typing import Any
from decimal import Decimal
from datetime import datetime, timezone

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.market_data.version_1.market_data import MarketData


class MarketDataProcessor(CyodaProcessor):
    """
    Processor for MarketData that handles validation, enrichment,
    and quality checks for market data feeds.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataProcessor",
            description="Processes market data feeds with validation and enrichment",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the MarketData with validation and enrichment.

        Args:
            entity: The MarketData to process (must be in 'validated' state)
            **kwargs: Additional processing parameters

        Returns:
            The processed market data with enrichments
        """
        try:
            self.logger.info(
                f"Processing MarketData for {getattr(entity, 'symbol', '<unknown>')}"
            )

            # Cast the entity to MarketData for type-safe operations
            market_data = cast_entity(entity, MarketData)

            # Perform data quality checks
            quality_results = await self._perform_quality_checks(market_data)
            market_data.data_quality = quality_results["quality"]
            
            # Enrich market data with calculated fields
            enrichments = await self._enrich_market_data(market_data)
            
            # Update calculated fields
            if enrichments["price_change"] is not None:
                market_data.price_change = enrichments["price_change"]
            if enrichments["price_change_percent"] is not None:
                market_data.price_change_percent = enrichments["price_change_percent"]
            if enrichments["vwap"] is not None:
                market_data.vwap = enrichments["vwap"]
            
            # Update processing timestamp
            market_data.processed_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Validate market status
            await self._validate_market_status(market_data)

            self.logger.info(
                f"MarketData for {market_data.symbol} processed successfully - "
                f"Quality: {market_data.data_quality}, Last Price: {market_data.last_price}"
            )

            return market_data

        except Exception as e:
            self.logger.error(
                f"Error processing market data for {getattr(entity, 'symbol', '<unknown>')}: {str(e)}"
            )
            raise

    async def _perform_quality_checks(self, market_data: MarketData) -> dict:
        """
        Perform data quality checks on market data.

        Args:
            market_data: The MarketData to check

        Returns:
            Dictionary containing quality assessment results
        """
        quality_issues = []
        
        # Check for stale data
        if market_data.is_stale():
            quality_issues.append("STALE_DATA")
        
        # Check price reasonableness
        if market_data.last_price and market_data.last_price <= 0:
            quality_issues.append("INVALID_PRICE")
        
        # Check bid-ask spread reasonableness
        spread = market_data.get_spread()
        if spread and market_data.last_price:
            spread_percentage = (spread / market_data.last_price) * 100
            if spread_percentage > 5:  # 5% spread threshold
                quality_issues.append("WIDE_SPREAD")
        
        # Check for crossed market
        if (market_data.bid_price and market_data.ask_price and 
            market_data.bid_price > market_data.ask_price):
            quality_issues.append("CROSSED_MARKET")
        
        # Check volume reasonableness
        if market_data.volume and market_data.volume < 0:
            quality_issues.append("INVALID_VOLUME")
        
        # Determine overall quality
        if not quality_issues:
            quality = "GOOD"
        elif len(quality_issues) == 1 and "STALE_DATA" in quality_issues:
            quality = "STALE"
        elif any(issue in ["INVALID_PRICE", "CROSSED_MARKET"] for issue in quality_issues):
            quality = "BAD"
        else:
            quality = "SUSPECT"
        
        return {
            "quality": quality,
            "issues": quality_issues,
        }

    async def _enrich_market_data(self, market_data: MarketData) -> dict:
        """
        Enrich market data with calculated fields.

        Args:
            market_data: The MarketData to enrich

        Returns:
            Dictionary containing enriched data
        """
        enrichments = {
            "price_change": None,
            "price_change_percent": None,
            "vwap": None,
        }
        
        # Calculate price change if we have both current and previous close
        if market_data.last_price and market_data.close_price:
            enrichments["price_change"] = market_data.last_price - market_data.close_price
            if market_data.close_price != 0:
                enrichments["price_change_percent"] = (enrichments["price_change"] / market_data.close_price) * 100
        
        # Calculate VWAP if we have volume and turnover
        if market_data.volume and market_data.turnover and market_data.volume > 0:
            enrichments["vwap"] = market_data.turnover / market_data.volume
        elif market_data.last_price:
            # Use last price as VWAP approximation if no volume data
            enrichments["vwap"] = market_data.last_price
        
        return enrichments

    async def _validate_market_status(self, market_data: MarketData) -> None:
        """
        Validate and update market status based on current time and exchange rules.

        Args:
            market_data: The MarketData to validate
        """
        # Simulate market hours validation
        current_hour = datetime.now(timezone.utc).hour
        
        # Simplified market hours (9:30 AM - 4:00 PM EST = 14:30 - 21:00 UTC)
        if 14 <= current_hour < 21:
            if market_data.market_status in ["UNKNOWN", "CLOSED"]:
                market_data.market_status = "OPEN"
                market_data.trading_session = "REGULAR"
        elif 12 <= current_hour < 14:
            market_data.market_status = "PRE_OPEN"
            market_data.trading_session = "PRE_MARKET"
        elif 21 <= current_hour < 24:
            market_data.market_status = "POST_CLOSE"
            market_data.trading_session = "POST_MARKET"
        else:
            market_data.market_status = "CLOSED"
            market_data.trading_session = None

    async def _check_circuit_breakers(self, market_data: MarketData) -> bool:
        """
        Check if circuit breakers should be triggered.

        Args:
            market_data: The MarketData to check

        Returns:
            True if circuit breaker should be triggered
        """
        if not market_data.price_change_percent:
            return False
        
        # Check for significant price movements (>10% change)
        if abs(market_data.price_change_percent) > 10:
            self.logger.warning(
                f"Large price movement detected for {market_data.symbol}: "
                f"{market_data.price_change_percent:.2f}%"
            )
            return True
        
        return False
