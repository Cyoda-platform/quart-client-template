"""
PaymentProcessingProcessor for Cyoda Claims Platform

Processes payments for approved claims.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.claim import Claim
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class PaymentProcessingProcessor(CyodaProcessor):
    """
    Processor for processing payments on Claim entities.
    Logs payment processing events.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PaymentProcessingProcessor",
            description="Processes payments for approved claims",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process payment for the Claim.

        Args:
            entity: The Claim to process payment for
            **kwargs: Additional processing parameters

        Returns:
            The claim unchanged
        """
        try:
            self.logger.info(
                f"Processing payment for claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            self._log_payment_processing(claim)

            self.logger.info(f"Payment processed for claim {claim.technical_id}")

            return claim

        except Exception as e:
            self.logger.error(
                f"Error processing payment for claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _log_payment_processing(self, claim: Claim) -> None:
        """
        Log the payment processing event to the claim's notes.

        Args:
            claim: The claim for which to process payment
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        payment_processing_note: Dict[str, Any] = {
            "timestamp": timestamp,
            "event_type": "PAYMENT_PROCESSING",
            "amount": claim.claim_amount,
            "description": f"Payment processed for claim {claim.claim_number}",
        }

        claim.notes.append(payment_processing_note)

        self.logger.debug(
            f"Logged payment processing for claim {claim.technical_id} at {timestamp}"
        )
