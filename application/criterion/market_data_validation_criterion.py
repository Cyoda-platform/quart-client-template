"""
MarketDataValidationCriterion for Trading Platform

Validates that MarketData meets all required quality and consistency
rules before it can proceed to processing and distribution.
"""

from typing import Any
from decimal import Decimal

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.market_data.version_1.market_data import MarketData


class MarketDataValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for MarketData that checks data quality
    and consistency rules before processing.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataValidationCriterion",
            description="Validates MarketData quality and consistency rules",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the market data meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be MarketData)
            **kwargs: Additional criteria parameters

        Returns:
            True if the market data meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating market data for {getattr(entity, 'symbol', '<unknown>')}"
            )

            # Cast the entity to MarketData for type-safe operations
            market_data = cast_entity(entity, MarketData)

            # Validate required fields
            if not market_data.symbol or len(market_data.symbol.strip()) == 0:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid symbol"
                )
                return False

            if not market_data.exchange or len(market_data.exchange.strip()) == 0:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid exchange"
                )
                return False

            if not market_data.data_source or len(market_data.data_source.strip()) == 0:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid data_source"
                )
                return False

            if not market_data.market_timestamp:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} missing market_timestamp"
                )
                return False

            # Validate price data consistency
            if not self._validate_price_data(market_data):
                return False

            # Validate bid-ask spread
            if not self._validate_bid_ask_spread(market_data):
                return False

            # Validate volume data
            if not self._validate_volume_data(market_data):
                return False

            # Validate daily statistics
            if not self._validate_daily_stats(market_data):
                return False

            # Check for stale data
            if market_data.is_stale():
                self.logger.warning(
                    f"MarketData {market_data.technical_id} for {market_data.symbol} is stale"
                )
                return False

            # Validate market status
            if market_data.market_status not in market_data.VALID_MARKET_STATUSES:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid market_status: {market_data.market_status}"
                )
                return False

            self.logger.info(
                f"MarketData for {market_data.symbol} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating market data {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

    def _validate_price_data(self, market_data: MarketData) -> bool:
        """Validate price data consistency."""
        # Check that prices are positive
        if market_data.last_price and market_data.last_price <= 0:
            self.logger.warning(
                f"MarketData {market_data.technical_id} has invalid last_price: {market_data.last_price}"
            )
            return False

        if market_data.bid_price and market_data.bid_price <= 0:
            self.logger.warning(
                f"MarketData {market_data.technical_id} has invalid bid_price: {market_data.bid_price}"
            )
            return False

        if market_data.ask_price and market_data.ask_price <= 0:
            self.logger.warning(
                f"MarketData {market_data.technical_id} has invalid ask_price: {market_data.ask_price}"
            )
            return False

        # Check that bid <= ask (no crossed market)
        if (market_data.bid_price and market_data.ask_price and 
            market_data.bid_price > market_data.ask_price):
            self.logger.warning(
                f"MarketData {market_data.technical_id} has crossed market: "
                f"bid {market_data.bid_price} > ask {market_data.ask_price}"
            )
            return False

        return True

    def _validate_bid_ask_spread(self, market_data: MarketData) -> bool:
        """Validate bid-ask spread reasonableness."""
        if not (market_data.bid_price and market_data.ask_price):
            return True  # No spread to validate

        spread = market_data.ask_price - market_data.bid_price
        if spread < 0:
            return False  # Already caught in price validation

        # Check for unreasonably wide spreads
        if market_data.last_price and market_data.last_price > 0:
            spread_percentage = (spread / market_data.last_price) * 100
            if spread_percentage > 10:  # 10% spread threshold
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has wide spread: {spread_percentage:.2f}%"
                )
                return False

        return True

    def _validate_volume_data(self, market_data: MarketData) -> bool:
        """Validate volume and turnover data."""
        # Check that volumes are non-negative
        if market_data.volume and market_data.volume < 0:
            self.logger.warning(
                f"MarketData {market_data.technical_id} has negative volume: {market_data.volume}"
            )
            return False

        if market_data.turnover and market_data.turnover < 0:
            self.logger.warning(
                f"MarketData {market_data.technical_id} has negative turnover: {market_data.turnover}"
            )
            return False

        if market_data.bid_size and market_data.bid_size < 0:
            self.logger.warning(
                f"MarketData {market_data.technical_id} has negative bid_size: {market_data.bid_size}"
            )
            return False

        if market_data.ask_size and market_data.ask_size < 0:
            self.logger.warning(
                f"MarketData {market_data.technical_id} has negative ask_size: {market_data.ask_size}"
            )
            return False

        # Check volume-turnover consistency
        if (market_data.volume and market_data.turnover and 
            market_data.volume > 0 and market_data.turnover > 0):
            implied_price = market_data.turnover / market_data.volume
            if market_data.last_price and abs(implied_price - market_data.last_price) / market_data.last_price > 0.5:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} volume-turnover inconsistency: "
                    f"implied price {implied_price} vs last price {market_data.last_price}"
                )
                return False

        return True

    def _validate_daily_stats(self, market_data: MarketData) -> bool:
        """Validate daily statistics consistency."""
        prices = [p for p in [market_data.open_price, market_data.high_price, 
                             market_data.low_price, market_data.close_price, 
                             market_data.last_price] if p is not None]
        
        if len(prices) < 2:
            return True  # Not enough data to validate

        # Check that high >= all other prices
        if market_data.high_price:
            for price in prices:
                if price > market_data.high_price:
                    self.logger.warning(
                        f"MarketData {market_data.technical_id} has price {price} > high {market_data.high_price}"
                    )
                    return False

        # Check that low <= all other prices
        if market_data.low_price:
            for price in prices:
                if price < market_data.low_price:
                    self.logger.warning(
                        f"MarketData {market_data.technical_id} has price {price} < low {market_data.low_price}"
                    )
                    return False

        return True
