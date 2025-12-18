import logging
from typing import Any

from application.entity.payment.version_1.payment import Payment
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class FraudDetectionCriterion(CyodaCriteriaChecker):
    def __init__(self) -> None:
        super().__init__(
            name="FraudDetectionCriterion",
            description="Evaluates fraud risk and determines payment action",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        try:
            self.logger.info(
                f"Evaluating fraud for Payment {getattr(entity, 'technical_id', '<unknown>')}"
            )

            payment = cast_entity(entity, Payment)

            fraud_score = self._calculate_fraud_score(payment)
            payment.fraud_score = fraud_score

            fraud_signals = self._extract_fraud_signals(payment)
            payment.fraud_signals = fraud_signals

            if fraud_score >= 75.0:
                payment.fraud_action = "DECLINE"
            elif fraud_score >= 50.0:
                payment.fraud_action = "REVIEW"
            else:
                payment.fraud_action = "ALLOW"

            self.logger.info(
                f"Payment {payment.technical_id} fraud score: {fraud_score}, action: {payment.fraud_action}"
            )

            return payment.fraud_action != "DECLINE"

        except Exception as e:
            self.logger.error(
                f"Error evaluating fraud for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _calculate_fraud_score(self, payment: Payment) -> float:
        score = 0.0

        if payment.amount > 5000:
            score += 20.0

        if payment.currency != payment.settlement_currency:
            score += 10.0

        if payment.payment_method_type == "card":
            score += 5.0

        return min(score, 100.0)

    def _extract_fraud_signals(self, payment: Payment) -> dict[str, Any]:
        return {
            "high_amount": payment.amount > 5000,
            "currency_mismatch": payment.currency != payment.settlement_currency,
            "payment_method": payment.payment_method_type,
            "timestamp": payment.created_at,
        }
