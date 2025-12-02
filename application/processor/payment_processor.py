import asyncio
import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.payment import Payment


class CreateDummyPaymentProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="CreateDummyPaymentProcessor",
            description="Creates a dummy payment record",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Creating dummy payment {getattr(entity, 'technical_id', '<unknown>')}"
            )

            payment = cast_entity(entity, Payment)
            payment.status = "INITIATED"

            self.logger.info(
                f"Dummy payment {payment.technical_id} created with status INITIATED"
            )

            return payment

        except Exception as e:
            self.logger.error(
                f"Error creating dummy payment {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class AutoMarkPaidProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="AutoMarkPaidProcessor",
            description="Auto-marks payment as PAID after ~3 seconds",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Auto-marking payment {getattr(entity, 'technical_id', '<unknown>')} as PAID"
            )

            payment = cast_entity(entity, Payment)

            await asyncio.sleep(3)

            payment.status = "PAID"

            self.logger.info(
                f"Payment {payment.technical_id} auto-marked as PAID"
            )

            return payment

        except Exception as e:
            self.logger.error(
                f"Error auto-marking payment {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

