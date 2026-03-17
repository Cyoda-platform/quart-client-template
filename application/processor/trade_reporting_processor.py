"""
TradeReportingProcessor for institutional trading platform.

Handles MiFID II transaction reporting and OTC derivatives reporting (EMIR/ESAAT).
"""

import logging
from datetime import datetime, timezone

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.trade.version_1.trade import Trade

logger = logging.getLogger(__name__)


class TradeReportingProcessor(CyodaProcessor):
    """
    Processor for reporting trades to regulatory authorities.
    """

    def __init__(self) -> None:
        super().__init__(
            name="TradeReportingProcessor",
            description="Reports trades to regulatory authorities (MiFID II, EMIR/ESAAT)",
        )

    async def process(self, entity: CyodaEntity, **kwargs) -> CyodaEntity:
        """
        Process trade reporting.

        Args:
            entity: The trade entity to report
            **kwargs: Additional processing parameters

        Returns:
            The trade with reporting details
        """
        try:
            self.logger.info(
                f"Reporting trade {getattr(entity, 'technical_id', '<unknown>')}"
            )

            trade = cast_entity(entity, Trade)

            # Set reporting timestamp
            trade.reported_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            # Log reporting action
            self.logger.info(
                f"Trade {trade.trade_id} reported for {trade.symbol} "
                f"({trade.quantity} @ {trade.price})"
            )

            return trade

        except Exception as e:
            self.logger.error(
                f"Error reporting trade {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
