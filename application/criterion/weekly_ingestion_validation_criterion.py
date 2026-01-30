"""
WeeklyIngestionValidationCriterion for validating fetched cat facts.

Validates that a CatFact entity has all required fields and valid data
before proceeding to the saved state.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.cat_fact.version_1.cat_fact import CatFact


class WeeklyIngestionValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for CatFact entities after API fetch.
    """

    def __init__(self) -> None:
        super().__init__(
            name="WeeklyIngestionValidationCriterion",
            description="Validates CatFact data after API fetch",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the CatFact entity is valid.

        Args:
            entity: The CyodaEntity to validate (expected to be CatFact)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity is valid, False otherwise
        """
        try:
            self.logger.info(
                f"Validating entity {getattr(entity, 'technical_id', '<unknown>')}"
            )

            cat_fact = cast_entity(entity, CatFact)

            # Validate required fields
            if not cat_fact.fact_text or len(cat_fact.fact_text.strip()) == 0:
                self.logger.warning(
                    f"Entity {cat_fact.technical_id} has empty fact text"
                )
                return False

            if not cat_fact.retrieved_at:
                self.logger.warning(
                    f"Entity {cat_fact.technical_id} has no retrieved_at timestamp"
                )
                return False

            self.logger.info(
                f"Entity {cat_fact.technical_id} validation passed"
            )
            return True

        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False

