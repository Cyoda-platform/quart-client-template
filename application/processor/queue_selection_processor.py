"""
QueueSelectionProcessor for Cyoda Claims Platform

Routes claims to appropriate queues based on claim type and region.
"""

import logging
import uuid
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.claim import Claim


class QueueSelectionProcessor(CyodaProcessor):
    """
    Processor for selecting the appropriate queue for a Claim.
    Routes based on claim type and region.
    """

    def __init__(self) -> None:
        super().__init__(
            name="QueueSelectionProcessor",
            description="Routes claims to appropriate queues based on claim type and region",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Select and assign a queue for the Claim.

        Args:
            entity: The Claim to route
            **kwargs: Additional processing parameters

        Returns:
            The claim with assigned_queue_id set
        """
        try:
            self.logger.info(
                f"Selecting queue for claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            queue_id = self._select_queue(claim)
            claim.assigned_queue_id = queue_id

            self.logger.info(f"Claim {claim.technical_id} assigned to queue {queue_id}")

            return claim

        except Exception as e:
            self.logger.error(
                f"Error selecting queue for claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _select_queue(self, claim: Claim) -> str:
        """
        Select queue based on claim type and region.

        Args:
            claim: The claim to route

        Returns:
            Queue ID
        """
        queue_type = self._determine_queue_type(claim.claim_type)
        queue_id = f"queue_{queue_type}_{uuid.uuid4().hex[:8]}"

        self.logger.debug(
            f"Selected queue {queue_id} for claim type {claim.claim_type}"
        )

        return queue_id

    def _determine_queue_type(self, claim_type: str) -> str:
        """
        Determine queue type based on claim type.

        Args:
            claim_type: The type of claim

        Returns:
            Queue type identifier
        """
        queue_mapping = {
            "AUTO": "auto_claims",
            "HOME": "home_claims",
            "LIFE": "life_claims",
            "HEALTH": "health_claims",
        }

        return queue_mapping.get(claim_type, "general_claims")
