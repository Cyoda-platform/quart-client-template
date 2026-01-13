from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.credit_report.version_1.credit_report import CreditReport


class CreditReportValidationCriterion(CyodaCriteriaChecker):
    def __init__(self) -> None:
        super().__init__(
            name="CreditReportValidationCriterion",
            description="Validates credit report data completeness and consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        try:
            self.logger.info(f"Validating credit report {getattr(entity, 'technical_id', '<unknown>')}")

            report = cast_entity(entity, CreditReport)

            if not report.applicant_id:
                self.logger.warning("Missing applicant_id")
                return False

            if not report.bureau_name:
                self.logger.warning("Missing bureau_name")
                return False

            valid_bureaus = ["EQUIFAX", "EXPERIAN", "TRANSUNION"]
            if report.bureau_name not in valid_bureaus:
                self.logger.warning(f"Invalid bureau: {report.bureau_name}")
                return False

            if report.credit_score and (report.credit_score < 300 or report.credit_score > 850):
                self.logger.warning(f"Invalid credit score: {report.credit_score}")
                return False

            if report.credit_utilization_percent < 0 or report.credit_utilization_percent > 100:
                self.logger.warning(f"Invalid utilization: {report.credit_utilization_percent}")
                return False

            if report.accounts_open < 0 or report.accounts_closed < 0:
                self.logger.warning("Invalid account counts")
                return False

            if report.total_credit_limit < 0 or report.total_credit_used < 0:
                self.logger.warning("Invalid credit amounts")
                return False

            self.logger.info(f"Credit report {report.technical_id} passed validation")
            return True

        except Exception as e:
            self.logger.error(f"Error validating credit report: {str(e)}")
            return False

