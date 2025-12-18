import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.payment.version_1.payment import Payment
from services.services import get_entity_service


class PaymentProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="PaymentProcessor",
            description="Processes payment authorization and generates authorization codes",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Processing Payment {getattr(entity, 'technical_id', '<unknown>')}"
            )

            payment = cast_entity(entity, Payment)

            if payment.fraud_action == "DECLINE":
                self.logger.info(
                    f"Payment {payment.technical_id} declined due to fraud score"
                )
                return payment

            authorization_code = self._generate_authorization_code()
            payment.authorization_code = authorization_code

            self.logger.info(
                f"Payment {payment.technical_id} authorized with code {authorization_code}"
            )

            return payment

        except Exception as e:
            self.logger.error(
                f"Error processing payment {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _generate_authorization_code(self) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_suffix = str(uuid.uuid4())[:8].upper()
        return f"AUTH-{timestamp}-{random_suffix}"

