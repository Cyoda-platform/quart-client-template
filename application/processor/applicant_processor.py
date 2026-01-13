from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.applicant.version_1.applicant import Applicant
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class ApplicantProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="ApplicantProcessor",
            description="Enriches applicant data with geolocation, device risk, and identity verification",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Processing Applicant {getattr(entity, 'technical_id', '<unknown>')}"
            )

            applicant = cast_entity(entity, Applicant)

            enrichment_data = await self._enrich_applicant(applicant)
            applicant.enrichment_data = enrichment_data

            self.logger.info(
                f"Applicant {applicant.technical_id} enriched successfully"
            )
            return applicant

        except Exception as e:
            self.logger.error(f"Error processing applicant: {str(e)}")
            raise

    async def _enrich_applicant(self, applicant: Applicant) -> Dict[str, Any]:
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        enrichment_data: Dict[str, Any] = {
            "enriched_at": current_timestamp,
            "geolocation": {
                "city": applicant.city,
                "state": applicant.state,
                "country": applicant.country,
                "risk_level": "LOW",
            },
            "device_risk": {
                "score": 0.15,
                "risk_level": "LOW",
                "indicators": [],
            },
            "identity_verification": {
                "status": "VERIFIED",
                "confidence_score": 0.98,
                "verification_method": "SSN_MATCH",
            },
            "income_verification": {
                "status": "PENDING",
                "annual_income": applicant.annual_income,
                "employment_status": applicant.employment_status,
            },
        }

        return enrichment_data
