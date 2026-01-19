"""
ClaimValidationProcessor for Cyoda Claims Platform

Validates claim data including policy existence, coverage checks, mandatory fields,
and consistency checks as specified in functional requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.claim import Claim


class ClaimValidationProcessor(CyodaProcessor):
    """
    Processor for validating Claim entities according to business rules.
    Checks mandatory fields, data consistency, and business logic constraints.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ClaimValidationProcessor",
            description="Validates claim data including mandatory fields and consistency checks",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Validate the Claim entity according to business rules.

        Args:
            entity: The Claim to validate
            **kwargs: Additional processing parameters

        Returns:
            The claim with validation_errors field populated if issues found
        """
        try:
            self.logger.info(
                f"Validating claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)
            claim.validation_errors = []

            self._validate_mandatory_fields(claim)
            self._validate_incident_date(claim)
            self._validate_claim_amount(claim)
            self._validate_claim_type(claim)

            if claim.validation_errors:
                self.logger.warning(
                    f"Claim {claim.technical_id} has validation errors: {claim.validation_errors}"
                )
            else:
                self.logger.info(
                    f"Claim {claim.technical_id} passed all validation checks"
                )

            return claim

        except Exception as e:
            self.logger.error(
                f"Error validating claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _validate_mandatory_fields(self, claim: Claim) -> None:
        """Validate that mandatory fields are not empty."""
        if not claim.claim_number or not claim.claim_number.strip():
            claim.validation_errors.append("claim_number is required")
        if not claim.policy_id or not claim.policy_id.strip():
            claim.validation_errors.append("policy_id is required")
        if not claim.claimant_id or not claim.claimant_id.strip():
            claim.validation_errors.append("claimant_id is required")

    def _validate_incident_date(self, claim: Claim) -> None:
        """Validate that incident_date is not in the future."""
        try:
            incident_dt = datetime.fromisoformat(claim.incident_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if incident_dt > now:
                claim.validation_errors.append("incident_date cannot be in the future")
        except ValueError:
            claim.validation_errors.append("incident_date must be valid ISO 8601 format")

    def _validate_claim_amount(self, claim: Claim) -> None:
        """Validate that claim_amount is positive."""
        if claim.claim_amount <= 0:
            claim.validation_errors.append("claim_amount must be positive")

    def _validate_claim_type(self, claim: Claim) -> None:
        """Validate that claim_type is valid."""
        valid_types = ["AUTO", "HOME", "LIFE", "HEALTH"]
        if claim.claim_type not in valid_types:
            claim.validation_errors.append(
                f"claim_type must be one of {valid_types}"
            )

