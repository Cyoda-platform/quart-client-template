"""
PaymentInstructionProcessor for Cyoda Claims Platform

Creates payment instructions for approved claims.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.claim import Claim


class PaymentInstructionProcessor(CyodaProcessor):
    """
    Processor for creating payment instructions on Claim entities.
    Logs payment instruction creation events.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PaymentInstructionProcessor",
            description="Creates payment instructions for approved claims",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Create payment instructions for the Claim.

        Args:
            entity: The Claim to create payment instructions for
            **kwargs: Additional processing parameters

        Returns:
            The claim unchanged
        """
        try:
            self.logger.info(
                f"Creating payment instructions for claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            self._log_payment_instruction(claim)

            self.logger.info(
                f"Payment instructions created for claim {claim.technical_id}"
            )

            return claim

        except Exception as e:
            self.logger.error(
                f"Error creating payment instructions for claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _log_payment_instruction(self, claim: Claim) -> None:
        """
        Log the payment instruction event to the claim's notes.

        Args:
            claim: The claim for which to create payment instructions
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        payment_instruction_note: Dict[str, Any] = {
            "timestamp": timestamp,
            "event_type": "PAYMENT_INSTRUCTION",
            "amount": claim.claim_amount,
            "description": f"Payment instruction created for claim {claim.claim_number}",
        }

        claim.notes.append(payment_instruction_note)

        self.logger.debug(
            f"Logged payment instruction for claim {claim.technical_id} at {timestamp}"
        )

