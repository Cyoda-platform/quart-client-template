from common.processor.base import CyodaCriteriaChecker
from common.entity.cyoda_entity import CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.market_data.version_1.market_data import MarketData
from datetime import datetime, timezone
from typing import Any

class MarketDataValidationCriterion(CyodaCriteriaChecker):
    def __init__(self) -> None:
        super().__init__(
            name="MarketDataValidationCriterion",
            description="Validates market data integrity and relevance"
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        try:
            market_data = cast_entity(entity, MarketData)

            # Validate symbol
            if not market_data.symbol or len(market_data.symbol) > 10:
                self.logger.warning(f"Invalid symbol: {market_data.symbol}")
                return False

            # Validate price
            if market_data.price <= 0:
                self.logger.warning(f"Invalid price: {market_data.price}")
                return False

            # Validate timestamp
            current_time = datetime.now(timezone.utc)
            if market_data.timestamp:
                try:
                    timestamp = datetime.fromisoformat(market_data.timestamp.replace("Z", "+00:00"))
                    # Check if timestamp is not in the future
                    if timestamp > current_time:
                        self.logger.warning(f"Future timestamp: {market_data.timestamp}")
                        return False
                except ValueError:
                    self.logger.warning(f"Invalid timestamp format: {market_data.timestamp}")
                    return False

            # Optional: Advanced validation (e.g., market-specific rules)
            allowed_markets = ["NASDAQ", "NYSE", "AMEX", "CRYPTO"]
            if market_data.market not in allowed_markets:
                self.logger.warning(f"Unsupported market: {market_data.market}")
                return False

            self.logger.info(f"Market data for {market_data.symbol} passed validation")
            return True

        except Exception as e:
            self.logger.error(f"Error validating market data: {str(e)}")
            return False