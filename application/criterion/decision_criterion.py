from typing import Any

from application.entity.decision.version_1.decision import Decision
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class DecisionCriterion(CyodaCriteriaChecker):
    def __init__(self) -> None:
        super().__init__(
            name="DecisionCriterion",
            description="Validates decision data and determines if approval criteria are met",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        try:
            self.logger.info(
                f"Evaluating decision {getattr(entity, 'technical_id', '<unknown>')}"
            )

            decision = cast_entity(entity, Decision)

            if not decision.applicant_id:
                self.logger.warning("Missing applicant_id")
                return False

            valid_outcomes = ["APPROVED", "DECLINED", "REFERRED"]
            if decision.decision_outcome not in valid_outcomes:
                self.logger.warning(
                    f"Invalid decision outcome: {decision.decision_outcome}"
                )
                return False

            if decision.decision_outcome == "APPROVED":
                if not decision.approved_amount or decision.approved_amount <= 0:
                    self.logger.warning("Approved decision missing approved_amount")
                    return False

                if not decision.approved_rate or decision.approved_rate < 0:
                    self.logger.warning("Approved decision missing approved_rate")
                    return False

            if decision.decision_outcome == "DECLINED":
                if not decision.decline_reason:
                    self.logger.warning("Declined decision missing decline_reason")
                    return False

            if decision.model_score and (
                decision.model_score < 0 or decision.model_score > 1
            ):
                self.logger.warning(f"Invalid model score: {decision.model_score}")
                return False

            self.logger.info(f"Decision {decision.technical_id} passed evaluation")
            return True

        except Exception as e:
            self.logger.error(f"Error evaluating decision: {str(e)}")
            return False
