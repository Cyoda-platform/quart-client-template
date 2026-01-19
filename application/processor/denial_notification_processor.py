"""
DenialNotificationProcessor for Cyoda Claims Platform

Sends denial notifications for denied claims.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.claim import Claim
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class DenialNotificationProcessor(CyodaProcessor):
    """
    Processor for sending denial notifications on Claim entities.
    Logs denial notification events.
    """

    def __init__(self) -> None:
        super().__init__(
            name="DenialNotificationProcessor",
            description="Sends denial notifications for denied claims",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Send denial notification for the Claim.

        Args:
            entity: The Claim to send denial notification for
            **kwargs: Additional processing parameters

        Returns:
            The claim unchanged
        """
        try:
            self.logger.info(
                f"Sending denial notification for claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            self._log_denial_notification(claim)

            self.logger.info(f"Denial notification sent for claim {claim.technical_id}")

            return claim

        except Exception as e:
            self.logger.error(
                f"Error sending denial notification for claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _log_denial_notification(self, claim: Claim) -> None:
        """
        Log the denial notification event to the claim's notes.

        Args:
            claim: The claim for which to send denial notification
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        denial_notification_note: Dict[str, Any] = {
            "timestamp": timestamp,
            "event_type": "DENIAL_NOTIFICATION",
            "description": f"Denial notification sent for claim {claim.claim_number}",
        }

        claim.notes.append(denial_notification_note)

        self.logger.debug(
            f"Logged denial notification for claim {claim.technical_id} at {timestamp}"
        )
