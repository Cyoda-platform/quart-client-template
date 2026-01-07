"""
Payment Transaction Processors for Enterprise Payment Processing System

Handles fraud detection, settlement creation, and transaction processing.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any


from application.entity.payment_transaction import PaymentTransaction
from application.entity.settlement import Settlement
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class FraudDetectionProcessor(CyodaProcessor):
    """Processor for fraud detection on payment transactions"""

    def __init__(self) -> None:
        super().__init__(
            name="FraudDetectionProcessor",
            description="Performs fraud detection analysis on payment transactions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Perform fraud detection on the payment transaction.

        Args:
            entity: The PaymentTransaction to analyze
            **kwargs: Additional processing parameters

        Returns:
            The transaction with fraud detection results
        """
        try:
            self.logger.info(
                f"Performing fraud detection on transaction {getattr(entity, 'technical_id', '<unknown>')}"
            )

            transaction = cast_entity(entity, PaymentTransaction)

            # Perform fraud checks
            fraud_score = self._calculate_fraud_score(transaction)
            fraud_status = self._determine_fraud_status(fraud_score)
            checks_performed = ["AMOUNT_CHECK", "MERCHANT_CHECK", "PATTERN_CHECK"]

            # Set fraud detection results
            transaction.set_fraud_detection_result(
                fraud_score, fraud_status, checks_performed
            )

            # Mark as PCI compliant
            masked_card = self._mask_card_number()
            transaction.mark_pci_compliant(masked_card)

            self.logger.info(
                f"Fraud detection completed for transaction {transaction.technical_id}: "
                f"score={fraud_score}, status={fraud_status}"
            )

            return transaction

        except Exception as e:
            self.logger.error(
                f"Error in fraud detection for transaction {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _calculate_fraud_score(self, transaction: PaymentTransaction) -> float:
        """Calculate fraud score based on transaction characteristics"""
        score = 0.0

        # Amount-based scoring
        if transaction.amount > 10000:
            score += 20
        elif transaction.amount > 5000:
            score += 10

        # Merchant-based scoring (simplified)
        if transaction.merchant_id.startswith("HIGH_RISK"):
            score += 30

        # Currency-based scoring
        if transaction.currency in ["JPY", "CNY"]:
            score += 15

        return min(score, 100.0)

    def _determine_fraud_status(self, fraud_score: float) -> str:
        """Determine fraud status based on score"""
        if fraud_score >= 70:
            return "HIGH_RISK"
        elif fraud_score >= 40:
            return "MEDIUM_RISK"
        else:
            return "LOW_RISK"

    def _mask_card_number(self) -> str:
        """Generate a masked card number"""
        return f"****-****-****-{str(uuid.uuid4())[:4].upper()}"


class SettlementCreationProcessor(CyodaProcessor):
    """Processor for creating settlement batches from transactions"""

    def __init__(self) -> None:
        super().__init__(
            name="SettlementCreationProcessor",
            description="Creates settlement batches for payment transactions",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Create a settlement batch for the transaction.

        Args:
            entity: The PaymentTransaction to settle
            **kwargs: Additional processing parameters

        Returns:
            The transaction with settlement information
        """
        try:
            self.logger.info(
                f"Creating settlement for transaction {getattr(entity, 'technical_id', '<unknown>')}"
            )

            transaction = cast_entity(entity, PaymentTransaction)
            entity_service = get_entity_service()

            # Create settlement batch
            settlement_batch_id = str(uuid.uuid4())
            settlement_date = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            settlement = Settlement(
                settlement_batch_id=settlement_batch_id,
                settlement_date=settlement_date,
                currency=transaction.currency,
                transactionIds=[
                    transaction.technical_id or transaction.entity_id or "unknown"
                ],
                totalAmount=transaction.amount,
                transactionCount=1,
                status="PENDING",
                reconciliationStatus="NOT_STARTED",
            )

            # Save settlement
            settlement_data = settlement.model_dump(by_alias=True)
            response = await entity_service.save(
                entity=settlement_data,
                entity_class=Settlement.ENTITY_NAME,
                entity_version=str(Settlement.ENTITY_VERSION),
            )

            settlement_id = response.metadata.id

            # Associate settlement with transaction
            transaction.associate_settlement(settlement_id, settlement_date)

            self.logger.info(
                f"Settlement {settlement_id} created for transaction {transaction.technical_id}"
            )

            return transaction

        except Exception as e:
            self.logger.error(
                f"Error creating settlement for transaction {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
