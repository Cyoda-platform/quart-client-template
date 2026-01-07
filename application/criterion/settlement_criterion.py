"""
Settlement Validation Criteria for Enterprise Payment Processing System

Validates settlement batches before reconciliation.
"""

from typing import Any

from application.entity.settlement import Settlement
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class SettlementValidationCriterion(CyodaCriteriaChecker):
    """Validation criterion for Settlement"""

    def __init__(self) -> None:
        super().__init__(
            name="SettlementValidationCriterion",
            description="Validates settlement batch business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the settlement meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Settlement)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating settlement {getattr(entity, 'technical_id', '<unknown>')}"
            )

            settlement = cast_entity(entity, Settlement)

            # Validate required fields
            if (
                not settlement.settlement_batch_id
                or len(settlement.settlement_batch_id.strip()) == 0
            ):
                self.logger.warning(
                    f"Settlement {settlement.technical_id} has invalid settlement_batch_id"
                )
                return False

            if (
                not settlement.settlement_date
                or len(settlement.settlement_date.strip()) == 0
            ):
                self.logger.warning(
                    f"Settlement {settlement.technical_id} has invalid settlement_date"
                )
                return False

            if settlement.currency not in settlement.ALLOWED_CURRENCIES:
                self.logger.warning(
                    f"Settlement {settlement.technical_id} has invalid currency: {settlement.currency}"
                )
                return False

            if settlement.total_amount < 0:
                self.logger.warning(
                    f"Settlement {settlement.technical_id} has negative total_amount: {settlement.total_amount}"
                )
                return False

            if settlement.transaction_count < 0:
                self.logger.warning(
                    f"Settlement {settlement.technical_id} has negative transaction_count: {settlement.transaction_count}"
                )
                return False

            # Validate transaction count matches transaction IDs
            if settlement.transaction_count != len(settlement.transaction_ids):
                self.logger.warning(
                    f"Settlement {settlement.technical_id} has mismatched transaction count: "
                    f"count={settlement.transaction_count}, ids={len(settlement.transaction_ids)}"
                )
                return False

            self.logger.info(
                f"Settlement {settlement.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating settlement {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
