import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.trade.version_1.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class TradeSettlementProcessor(CyodaProcessor):
    """Processes trade settlement and updates settlement status."""

    def __init__(self) -> None:
        super().__init__(
            name="TradeSettlementProcessor",
            description="Processes trade settlement and updates positions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process trade settlement.

        Args:
            entity: The Trade entity to process
            **kwargs: Additional processing parameters

        Returns:
            Updated trade entity
        """
        try:
            trade = cast_entity(entity, Trade)

            self.logger.info(f"Processing settlement for trade {trade.entity_id}")

            trade.settled_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(f"Trade {trade.entity_id} settled successfully")
            return trade

        except Exception as e:
            self.logger.error(f"Error processing trade settlement: {str(e)}")
            raise
