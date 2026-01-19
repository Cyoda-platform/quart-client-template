"""
FraudDeterminationProcessor for Cyoda Claims Platform

Determines fraud status by analyzing investigation notes.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.fraud_alert import FraudAlert


class FraudDeterminationProcessor(CyodaProcessor):
    """
    Processor for determining fraud status on FraudAlert entities.
    Analyzes investigation notes and updates alert status.
    """

    def __init__(self) -> None:
        super().__init__(
            name="FraudDeterminationProcessor",
            description="Determines fraud status based on investigation notes",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Determine fraud status for the FraudAlert.

        Args:
            entity: The FraudAlert to analyze
            **kwargs: Additional processing parameters

        Returns:
            The FraudAlert with updated status
        """
        try:
            self.logger.info(
                f"Determining fraud status for alert {getattr(entity, 'technical_id', '<unknown>')}"
            )

            fraud_alert = cast_entity(entity, FraudAlert)

            if fraud_alert.investigation_notes:
                self._analyze_investigation_notes(fraud_alert)
                self.logger.info(
                    f"FraudAlert {fraud_alert.technical_id} status updated to {fraud_alert.status}"
                )
            else:
                self.logger.debug(
                    f"FraudAlert {fraud_alert.technical_id} has no investigation notes yet"
                )

            return fraud_alert

        except Exception as e:
            self.logger.error(
                f"Error determining fraud status for alert {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _analyze_investigation_notes(self, fraud_alert: FraudAlert) -> None:
        """
        Analyze investigation notes to determine fraud status.

        Args:
            fraud_alert: The FraudAlert to analyze
        """
        if not fraud_alert.investigation_notes:
            return

        last_note = fraud_alert.investigation_notes[-1]

        if isinstance(last_note, dict):
            conclusion = last_note.get("conclusion", "").lower()

            if "confirmed" in conclusion or "fraud" in conclusion:
                fraud_alert.status = "Closed"
                self.logger.debug(
                    f"Fraud confirmed for alert {fraud_alert.technical_id}"
                )
            elif "not fraud" in conclusion or "cleared" in conclusion:
                fraud_alert.status = "Resolved"
                self.logger.debug(f"Fraud cleared for alert {fraud_alert.technical_id}")

        fraud_alert.update_timestamp()
