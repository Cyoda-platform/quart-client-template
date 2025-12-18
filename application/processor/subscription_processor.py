import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.subscription.version_1.subscription import Subscription
from services.services import get_entity_service


class SubscriptionProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="SubscriptionProcessor",
            description="Generates invoices and manages subscription billing cycles",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        try:
            self.logger.info(
                f"Processing Subscription {getattr(entity, 'technical_id', '<unknown>')}"
            )

            subscription = cast_entity(entity, Subscription)

            invoice_id = str(uuid.uuid4())
            current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            subscription.last_billing_date = current_time

            next_billing = self._calculate_next_billing_date(subscription)
            subscription.next_billing_date = next_billing

            self.logger.info(
                f"Subscription {subscription.technical_id} invoice {invoice_id} generated"
            )

            return subscription

        except Exception as e:
            self.logger.error(
                f"Error processing subscription {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _calculate_next_billing_date(self, subscription: Subscription) -> str:
        now = datetime.now(timezone.utc)

        if subscription.billing_interval == "daily":
            next_date = now + timedelta(days=1)
        elif subscription.billing_interval == "weekly":
            next_date = now + timedelta(weeks=1)
        elif subscription.billing_interval == "monthly":
            next_date = now + timedelta(days=30)
        elif subscription.billing_interval == "yearly":
            next_date = now + timedelta(days=365)
        else:
            next_date = now + timedelta(days=30)

        return next_date.isoformat().replace("+00:00", "Z")

