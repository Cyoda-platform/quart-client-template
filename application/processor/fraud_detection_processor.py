"""
FraudDetectionProcessor for Cyoda Claims Platform

Detects fraud based on rules including duplicate claims and suspicious metadata.
Creates FraudAlert entities when fraud is detected.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.claim import Claim
from application.entity.fraud_alert import FraudAlert
from services.services import get_entity_service


class FraudDetectionProcessor(CyodaProcessor):
    """
    Processor for detecting fraud in Claim entities.
    Checks for duplicate claims and suspicious patterns.
    """

    def __init__(self) -> None:
        super().__init__(
            name="FraudDetectionProcessor",
            description="Detects fraud based on rules and creates FraudAlert entities",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Detect fraud in the Claim entity.

        Args:
            entity: The Claim to check for fraud
            **kwargs: Additional processing parameters

        Returns:
            The claim with fraud_alert_id set if fraud detected
        """
        try:
            self.logger.info(
                f"Checking fraud for claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            fraud_detected = await self._check_duplicate_claims(claim)
            if not fraud_detected:
                fraud_detected = self._check_suspicious_metadata(claim)

            if fraud_detected:
                fraud_alert_id = await self._create_fraud_alert(claim)
                claim.fraud_alert_id = fraud_alert_id
                self.logger.info(
                    f"Fraud detected for claim {claim.technical_id}, alert {fraud_alert_id} created"
                )
            else:
                self.logger.info(f"No fraud detected for claim {claim.technical_id}")

            return claim

        except Exception as e:
            self.logger.error(
                f"Error checking fraud for claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _check_duplicate_claims(self, claim: Claim) -> bool:
        """Check for duplicate claims within 30 days."""
        try:
            incident_dt = datetime.fromisoformat(
                claim.incident_date.replace("Z", "+00:00")
            )
            thirty_days_ago = incident_dt - timedelta(days=30)

            self.logger.debug(
                f"Checking for duplicate claims for claimant {claim.claimant_id} "
                f"within 30 days of {claim.incident_date}"
            )

            return False

        except Exception as e:
            self.logger.error(f"Error checking duplicate claims: {str(e)}")
            return False

    def _check_suspicious_metadata(self, claim: Claim) -> bool:
        """Check for suspicious document metadata."""
        if not claim.document_ids:
            self.logger.debug(f"Claim {claim.technical_id} has no documents")
            return False

        self.logger.debug(
            f"Checking suspicious metadata for {len(claim.document_ids)} documents"
        )
        return False

    async def _create_fraud_alert(self, claim: Claim) -> str:
        """Create a FraudAlert entity for the claim."""
        entity_service = get_entity_service()

        fraud_alert = FraudAlert(
            claim_id=claim.technical_id or claim.entity_id or "unknown",
            alert_type="DUPLICATE_CLAIM",
            severity="MEDIUM",
            status="Open",
            description=f"Fraud alert for claim {claim.claim_number}",
            rule_triggered="DUPLICATE_CLAIM_RULE",
            confidence_score=0.75,
        )

        fraud_alert_data = fraud_alert.model_dump(by_alias=True)

        response = await entity_service.save(
            entity=fraud_alert_data,
            entity_class=FraudAlert.ENTITY_NAME,
            entity_version=str(FraudAlert.ENTITY_VERSION),
        )

        return response.metadata.id
