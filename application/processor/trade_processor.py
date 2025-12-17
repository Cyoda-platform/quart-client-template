import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from application.entity.trade.version_1.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class TradeProcessor(CyodaProcessor):
    """
    Processor for Trade that handles trade confirmation and settlement logic.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TradeProcessor",
            description="Processes Trade instances and confirms execution",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Trade for confirmation.

        Args:
            entity: The Trade to process
            **kwargs: Additional processing parameters

        Returns:
            The processed trade with confirmation details
        """
        try:
            self.logger.info(
                f"Processing Trade {getattr(entity, 'technical_id', '<unknown>')}"
            )

            trade = cast_entity(entity, Trade)

            if not trade.trade_id:
                trade.trade_id = f"TRD_{uuid.uuid4().hex[:12].upper()}"

            trade.confirmed_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            if trade.quantity and trade.price:
                trade.gross_amount = trade.quantity * trade.price
                trade.commission = trade.gross_amount * 0.001
                trade.net_amount = trade.gross_amount - trade.commission

            trade.status = "CONFIRMED"

            self.logger.info(f"Trade {trade.trade_id} confirmed successfully")

            return trade

        except Exception as e:
            self.logger.error(
                f"Error processing trade {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
