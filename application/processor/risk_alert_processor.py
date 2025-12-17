import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.risk_alert.version_1.risk_alert import RiskAlert
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class RiskAlertProcessor(CyodaProcessor):
    """
    Processor for RiskAlert that handles alert triggering and notification.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskAlertProcessor",
            description="Processes RiskAlert instances and triggers notifications",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the RiskAlert for triggering.

        Args:
            entity: The RiskAlert to process
            **kwargs: Additional processing parameters

        Returns:
            The processed alert with trigger details
        """
        try:
            self.logger.info(
                f"Processing RiskAlert {getattr(entity, 'technical_id', '<unknown>')}"
            )

            alert = cast_entity(entity, RiskAlert)

            alert.triggered_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            alert.status = "ACTIVE"

            self.logger.warning(
                f"Risk Alert triggered for account {alert.account}: {alert.message}"
            )

            return alert

        except Exception as e:
            self.logger.error(
                f"Error processing risk alert {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
