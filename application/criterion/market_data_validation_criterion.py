"""
MarketDataValidationCriterion for Real-Time Trading Platform

Validates that MarketData meets all required business rules before it can
proceed to the enrichment stage.
"""

from typing import Any

from application.entity.market_data.version_1.market_data import MarketData
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class MarketDataValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for MarketData that checks all business rules
    before the entity can proceed to enrichment stage.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataValidationCriterion",
            description="Validates MarketData business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the MarketData meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be MarketData)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating MarketData {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to MarketData for type-safe operations
            market_data = cast_entity(entity, MarketData)

            # Validate required fields
            if not market_data.symbol or len(market_data.symbol.strip()) == 0:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid symbol"
                )
                return False

            if market_data.instrument_type not in MarketData.ALLOWED_INSTRUMENT_TYPES:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid instrument type: {market_data.instrument_type}"
                )
                return False

            if market_data.price <= 0:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid price: {market_data.price}"
                )
                return False

            if market_data.volume < 0:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid volume: {market_data.volume}"
                )
                return False

            if market_data.market_status not in MarketData.ALLOWED_MARKET_STATUSES:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid market status: {market_data.market_status}"
                )
                return False

            if not market_data.exchange or len(market_data.exchange.strip()) == 0:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has invalid exchange"
                )
                return False

            # Validate bid/ask price consistency if both are provided
            if (
                market_data.bid_price is not None
                and market_data.ask_price is not None
                and market_data.bid_price > market_data.ask_price
            ):
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has bid price higher than ask price"
                )
                return False

            # Validate price reasonableness (basic sanity check)
            if market_data.price > 1000000:  # Extremely high price
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has unreasonably high price: {market_data.price}"
                )
                return False

            # Check if data is not too stale (within 5 minutes for validation)
            if market_data.is_stale(max_age_seconds=300):
                self.logger.warning(
                    f"MarketData {market_data.technical_id} has stale timestamp"
                )
                return False

            self.logger.info(
                f"MarketData {market_data.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating MarketData {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
