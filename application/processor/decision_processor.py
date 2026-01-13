from datetime import datetime, timezone
from typing import Any, Dict, List

from application.entity.decision.version_1.decision import Decision
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class DecisionProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="DecisionProcessor",
            description="Evaluates applicant and generates credit decision with audit trail",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Processing Decision {getattr(entity, 'technical_id', '<unknown>')}"
            )

            decision = cast_entity(entity, Decision)

            audit_trail = self._build_audit_trail(decision)
            decision.audit_trail = audit_trail

            self.logger.info(f"Decision {decision.technical_id} evaluated successfully")
            return decision

        except Exception as e:
            self.logger.error(f"Error processing decision: {str(e)}")
            raise

    def _build_audit_trail(self, decision: Decision) -> List[Dict[str, Any]]:
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        trail: List[Dict[str, Any]] = [
            {
                "timestamp": current_timestamp,
                "event": "decision_initiated",
                "details": f"Decision evaluation started for applicant {decision.applicant_id}",
            },
        ]

        if decision.credit_report_id:
            trail.append(
                {
                    "timestamp": current_timestamp,
                    "event": "credit_report_retrieved",
                    "details": f"Credit report {decision.credit_report_id} retrieved",
                }
            )

        if decision.model_version_id:
            trail.append(
                {
                    "timestamp": current_timestamp,
                    "event": "model_inference",
                    "details": f"Model {decision.model_version_id} inference completed with score {decision.model_score}",
                }
            )

        trail.append(
            {
                "timestamp": current_timestamp,
                "event": "decision_made",
                "details": f"Decision outcome: {decision.decision_outcome}",
            }
        )

        return trail
