"""
FraudAlertCreationProcessor for Cyoda Claims Platform

Creates FraudAlert entities with appropriate alert type, severity, and status.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.fraud_alert import FraudAlert


class FraudAlertCreationProcessor(CyodaProcessor):
    """
    Processor for creating FraudAlert entities.
    Sets alert properties and initializes investigation tracking.
    """

    def __init__(self) -> None:
        super().__init__(
            name="FraudAlertCreationProcessor",
            description="Creates FraudAlert entities with appropriate properties",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Create or process a FraudAlert entity.

        Args:
            entity: The FraudAlert to process
            **kwargs: Additional processing parameters

        Returns:
            The FraudAlert entity
        """
        try:
            self.logger.info(
                f"Processing FraudAlert {getattr(entity, 'technical_id', '<unknown>')}"
            )

            fraud_alert = cast_entity(entity, FraudAlert)

            self._validate_alert_properties(fraud_alert)

            self.logger.info(
                f"FraudAlert {fraud_alert.technical_id} created successfully"
            )

            return fraud_alert

        except Exception as e:
            self.logger.error(
                f"Error processing FraudAlert {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _validate_alert_properties(self, fraud_alert: FraudAlert) -> None:
        """
        Validate that FraudAlert has all required properties.

        Args:
            fraud_alert: The FraudAlert to validate
        """
        if not fraud_alert.claim_id:
            raise ValueError("FraudAlert must have a claim_id")

        if not fraud_alert.alert_type:
            raise ValueError("FraudAlert must have an alert_type")

        if not fraud_alert.severity:
            raise ValueError("FraudAlert must have a severity level")

        if not fraud_alert.status:
            raise ValueError("FraudAlert must have a status")

        if not fraud_alert.description:
            raise ValueError("FraudAlert must have a description")

        self.logger.debug(f"FraudAlert {fraud_alert.technical_id} properties validated")
