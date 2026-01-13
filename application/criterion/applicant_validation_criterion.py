from typing import Any

from application.entity.applicant.version_1.applicant import Applicant
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class ApplicantValidationCriterion(CyodaCriteriaChecker):
    def __init__(self) -> None:
        super().__init__(
            name="ApplicantValidationCriterion",
            description="Validates applicant data completeness and business rules",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        try:
            self.logger.info(
                f"Validating applicant {getattr(entity, 'technical_id', '<unknown>')}"
            )

            applicant = cast_entity(entity, Applicant)

            if not applicant.first_name or len(applicant.first_name.strip()) < 2:
                self.logger.warning(f"Invalid first name: {applicant.first_name}")
                return False

            if not applicant.last_name or len(applicant.last_name.strip()) < 2:
                self.logger.warning(f"Invalid last name: {applicant.last_name}")
                return False

            if "@" not in applicant.email:
                self.logger.warning(f"Invalid email: {applicant.email}")
                return False

            if not applicant.phone or len(applicant.phone) < 10:
                self.logger.warning(f"Invalid phone: {applicant.phone}")
                return False

            if applicant.annual_income < 0:
                self.logger.warning(f"Invalid income: {applicant.annual_income}")
                return False

            if applicant.loan_amount <= 0:
                self.logger.warning(f"Invalid loan amount: {applicant.loan_amount}")
                return False

            if applicant.loan_term_months <= 0 or applicant.loan_term_months > 360:
                self.logger.warning(f"Invalid loan term: {applicant.loan_term_months}")
                return False

            valid_statuses = ["EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "RETIRED"]
            if applicant.employment_status not in valid_statuses:
                self.logger.warning(
                    f"Invalid employment status: {applicant.employment_status}"
                )
                return False

            valid_purposes = ["PERSONAL", "AUTO", "HOME", "BUSINESS"]
            if applicant.loan_purpose not in valid_purposes:
                self.logger.warning(f"Invalid loan purpose: {applicant.loan_purpose}")
                return False

            self.logger.info(f"Applicant {applicant.technical_id} passed validation")
            return True

        except Exception as e:
            self.logger.error(f"Error validating applicant: {str(e)}")
            return False
