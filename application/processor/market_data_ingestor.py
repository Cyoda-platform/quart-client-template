"""
MarketDataIngestor processor for institutional trading platform.

Ingests external market data feeds and emits market_tick entities.
Triggers position_valuation workflow.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class MarketDataIngestor(CyodaProcessor):
    """
    Ingests market data from external feeds and creates market_tick entities.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataIngestor",
            description="Ingests market data and creates market_tick entities",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Ingest market data and create market_tick entity.

        Args:
            entity: The market data entity to ingest
            **kwargs: Additional ingestion parameters

        Returns:
            The ingested market data entity
        """
        try:
            self.logger.info(
                f"Ingesting market data {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Validate market data
            self._validate_market_data(entity)

            # Normalize market data
            normalized_data = self._normalize_market_data(entity)

            # Create market_tick entity
            await self._create_market_tick(normalized_data)

            # Store ingestion metadata
            if not hasattr(entity, "ingestionMetadata"):
                entity.ingestionMetadata = {}
            entity.ingestionMetadata["normalized"] = normalized_data
            entity.ingestionMetadata["ingested_at"] = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(
                f"Market data ingestion completed for {normalized_data.get('instrumentId')}"
            )
            return entity

        except Exception as e:
            self.logger.error(f"Error ingesting market data: {str(e)}")
            raise

    def _validate_market_data(self, entity: CyodaEntity) -> None:
        """
        Validate market data structure.

        Args:
            entity: The market data entity

        Raises:
            ValueError: If validation fails
        """
        # TODO: Validate against market data schema
        # - Check required fields (instrumentId, timestamp, price data)
        # - Validate price ranges
        # - Check timestamp ordering
        # - Detect stale data

        required_fields = ["instrumentId", "timestamp"]
        for field in required_fields:
            if not hasattr(entity, field) or getattr(entity, field) is None:
                raise ValueError(f"Market data missing required field: {field}")

    def _normalize_market_data(self, entity: CyodaEntity) -> Dict[str, Any]:
        """
        Normalize market data from various sources.

        Args:
            entity: The market data entity

        Returns:
            Normalized market data dictionary
        """
        # TODO: Implement normalization for different data sources
        # - Bloomberg
        # - Reuters
        # - Exchange feeds
        # - Broker APIs

        normalized: Dict[str, Any] = {
            "instrumentId": getattr(entity, "instrumentId", None),
            "timestamp": getattr(entity, "timestamp", None),
            "bid": getattr(entity, "bid", None),
            "ask": getattr(entity, "ask", None),
            "lastPrice": getattr(entity, "lastPrice", None),
            "bidSize": getattr(entity, "bidSize", None),
            "askSize": getattr(entity, "askSize", None),
            "volume": getattr(entity, "volume", None),
            "source": getattr(entity, "source", "UNKNOWN"),
        }

        self.logger.debug(f"Normalized market data: {normalized}")
        return normalized

    async def _create_market_tick(self, market_data: Dict[str, Any]) -> None:
        """
        Create a market_tick entity from normalized data.

        Args:
            market_data: The normalized market data
        """
        # TODO: Integrate with entity service to create market_tick
        # - Use entity service to save market_tick
        # - Trigger position_valuation workflow
        # - Handle batch ingestion for high-frequency data

        entity_service = get_entity_service()

        market_tick = {
            "id": str(uuid.uuid4()),
            "instrumentId": market_data.get("instrumentId"),
            "timestamp": market_data.get("timestamp"),
            "bid": market_data.get("bid"),
            "ask": market_data.get("ask"),
            "lastPrice": market_data.get("lastPrice"),
            "bidSize": market_data.get("bidSize"),
            "askSize": market_data.get("askSize"),
        }

        try:
            response = await entity_service.save(
                entity=market_tick,
                entity_class="market_tick",
                entity_version="1",
            )
            self.logger.info(
                f"Created market_tick {response.metadata.id} for {market_data.get('instrumentId')}"
            )
        except Exception as e:
            self.logger.error(f"Failed to create market_tick: {str(e)}")
            raise
