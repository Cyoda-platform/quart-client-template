"""
AssignmentHistoryProcessor for Cyoda Claims Platform

Records assignment history by updating assigned_adjuster_id and logging timestamps.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.claim import Claim


class AssignmentHistoryProcessor(CyodaProcessor):
    """
    Processor for recording assignment history on Claim entities.
    Updates assigned_adjuster_id and logs assignment timestamps.
    """

    def __init__(self) -> None:
        super().__init__(
            name="AssignmentHistoryProcessor",
            description="Records assignment history and updates assigned adjuster",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Record assignment history for the Claim.

        Args:
            entity: The Claim to update
            **kwargs: Additional processing parameters (may include adjuster_id)

        Returns:
            The claim with updated assignment information
        """
        try:
            self.logger.info(
                f"Recording assignment history for claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            adjuster_id = kwargs.get("adjuster_id", self._generate_adjuster_id())
            claim.assigned_adjuster_id = adjuster_id

            self._log_assignment(claim, adjuster_id)

            self.logger.info(
                f"Claim {claim.technical_id} assigned to adjuster {adjuster_id}"
            )

            return claim

        except Exception as e:
            self.logger.error(
                f"Error recording assignment for claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _generate_adjuster_id(self) -> str:
        """Generate a unique adjuster ID."""
        return f"adjuster_{uuid.uuid4().hex[:8]}"

    def _log_assignment(self, claim: Claim, adjuster_id: str) -> None:
        """
        Log the assignment event to the claim's notes.

        Args:
            claim: The claim being assigned
            adjuster_id: The ID of the assigned adjuster
        """
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        assignment_note: Dict[str, Any] = {
            "timestamp": timestamp,
            "event_type": "ASSIGNMENT",
            "adjuster_id": adjuster_id,
            "description": f"Claim assigned to adjuster {adjuster_id}",
        }

        claim.notes.append(assignment_note)

        self.logger.debug(
            f"Logged assignment event for claim {claim.technical_id} at {timestamp}"
        )

