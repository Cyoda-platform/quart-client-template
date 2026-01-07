"""
Payment Transaction Validation Criteria for Enterprise Payment Processing System

Validates payment transactions before processing.
"""

from typing import Any

from application.entity.payment_transaction import PaymentTransaction
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class PaymentTransactionValidationCriterion(CyodaCriteriaChecker):
    """Validation criterion for PaymentTransaction"""

    def __init__(self) -> None:
        super().__init__(
            name="PaymentTransactionValidationCriterion",
            description="Validates payment transaction business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the payment transaction meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be PaymentTransaction)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating payment transaction {getattr(entity, 'technical_id', '<unknown>')}"
            )

            transaction = cast_entity(entity, PaymentTransaction)

            # Validate required fields
            if (
                not transaction.transaction_id
                or len(transaction.transaction_id.strip()) == 0
            ):
                self.logger.warning(
                    f"Transaction {transaction.technical_id} has invalid transaction_id"
                )
                return False

            if transaction.amount <= 0:
                self.logger.warning(
                    f"Transaction {transaction.technical_id} has invalid amount: {transaction.amount}"
                )
                return False

            if transaction.currency not in transaction.ALLOWED_CURRENCIES:
                self.logger.warning(
                    f"Transaction {transaction.technical_id} has invalid currency: {transaction.currency}"
                )
                return False

            if not transaction.merchant_id or len(transaction.merchant_id.strip()) == 0:
                self.logger.warning(
                    f"Transaction {transaction.technical_id} has invalid merchant_id"
                )
                return False

            if not transaction.customer_id or len(transaction.customer_id.strip()) == 0:
                self.logger.warning(
                    f"Transaction {transaction.technical_id} has invalid customer_id"
                )
                return False

            self.logger.info(
                f"Payment transaction {transaction.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating payment transaction {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
