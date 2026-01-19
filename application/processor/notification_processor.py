"""
NotificationProcessor for Cyoda Claims Platform

Sends notifications for claim events.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.claim import Claim


class NotificationProcessor(CyodaProcessor):
    """
    Processor for sending notifications related to Claim entities.
    Logs notification events.
    """

    def __init__(self) -> None:
        super().__init__(
            name="NotificationProcessor",
            description="Sends notifications for claim events",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Send notifications for the Claim.

        Args:
            entity: The Claim to send notifications for
            **kwargs: Additional processing parameters

        Returns:
            The entity unchanged
        """
        try:
            self.logger.info(
                f"Sending notifications for claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            self._log_notification_event(claim)

            self.logger.info(f"Notifications sent for claim {claim.technical_id}")

            return claim

        except Exception as e:
            self.logger.error(
                f"Error sending notifications for claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _log_notification_event(self, claim: Claim) -> None:
        """
        Log the notification event to the claim's notes.

        Args:
            claim: The claim for which to log notification
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        notification_note: Dict[str, Any] = {
            "timestamp": timestamp,
            "event_type": "NOTIFICATION",
            "description": f"Notification sent for claim {claim.claim_number}",
        }

        claim.notes.append(notification_note)

        self.logger.debug(
            f"Logged notification event for claim {claim.technical_id} at {timestamp}"
        )
