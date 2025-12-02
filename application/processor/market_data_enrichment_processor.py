"""
MarketDataEnrichmentProcessor for Real-Time Trading Platform

Handles enrichment of market data with calculated fields like spread,
volatility, and additional market indicators.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.market_data.version_1.market_data import MarketData
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class MarketDataEnrichmentProcessor(CyodaProcessor):
    """
    Processor for MarketData that enriches market data with calculated fields
    and additional market indicators.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataEnrichmentProcessor",
            description="Enriches MarketData with calculated fields and market indicators",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Enrich the MarketData with calculated fields and indicators.

        Args:
            entity: The MarketData to enrich (must be in 'validated' state)
            **kwargs: Additional processing parameters

        Returns:
            The enriched entity with calculated fields
        """
        try:
            self.logger.info(
                f"Enriching MarketData {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to MarketData for type-safe operations
            market_data = cast_entity(entity, MarketData)

            # Calculate spread if bid/ask prices are available
            spread = market_data.calculate_spread()
            if spread is not None:
                market_data.spread = spread

            # Create enrichment data with market indicators
            enrichment_data = self._create_enrichment_data(market_data)
            market_data.set_enrichment_data(enrichment_data)

            # Log enrichment completion
            self.logger.info(
                f"MarketData {market_data.technical_id} enriched successfully"
            )

            return market_data

        except Exception as e:
            self.logger.error(
                f"Error enriching MarketData {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _create_enrichment_data(self, market_data: MarketData) -> Dict[str, Any]:
        """
        Create enrichment data with market indicators and metadata.

        Args:
            market_data: The MarketData entity to enrich

        Returns:
            Dictionary containing enrichment data
        """
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        enrichment_data: Dict[str, Any] = {
            "enriched_at": current_timestamp,
            "data_quality": self._assess_data_quality(market_data),
            "market_indicators": self._calculate_market_indicators(market_data),
            "enrichment_version": "1.0",
        }

        return enrichment_data

    def _assess_data_quality(self, market_data: MarketData) -> str:
        """
        Assess the quality of market data.

        Args:
            market_data: The MarketData entity

        Returns:
            Data quality assessment: HIGH, MEDIUM, or LOW
        """
        quality_score = 0

        # Check if all price fields are available
        if market_data.bid_price is not None and market_data.ask_price is not None:
            quality_score += 2

        # Check if data is recent (not stale)
        if not market_data.is_stale(max_age_seconds=30):
            quality_score += 2

        # Check if volume is reasonable
        if market_data.volume > 0:
            quality_score += 1

        # Determine quality level
        if quality_score >= 4:
            return "HIGH"
        elif quality_score >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def _calculate_market_indicators(self, market_data: MarketData) -> Dict[str, Any]:
        """
        Calculate basic market indicators.

        Args:
            market_data: The MarketData entity

        Returns:
            Dictionary containing market indicators
        """
        indicators: Dict[str, Any] = {
            "has_spread": market_data.spread is not None,
            "is_market_open": market_data.is_market_open(),
            "volume_category": self._categorize_volume(market_data.volume),
        }

        # Calculate spread percentage if available
        if market_data.spread is not None and market_data.price > 0:
            indicators["spread_percentage"] = (
                market_data.spread / market_data.price
            ) * 100

        return indicators

    def _categorize_volume(self, volume: int) -> str:
        """
        Categorize trading volume.

        Args:
            volume: Trading volume

        Returns:
            Volume category: HIGH, MEDIUM, or LOW
        """
        if volume >= 1000000:
            return "HIGH"
        elif volume >= 100000:
            return "MEDIUM"
        else:
            return "LOW"
