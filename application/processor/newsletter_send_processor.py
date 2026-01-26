"""
NewsletterSendProcessor for the newsletter application.

Sends the newsletter to all active subscribers and tracks delivery status.
"""

import logging
from typing import Any

from application.entity.newsletter import Newsletter
from application.entity.subscriber import Subscriber
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class NewsletterSendProcessor(CyodaProcessor):
    """
    Processor that sends the newsletter to all active subscribers
    and tracks delivery status.
    """

    def __init__(self) -> None:
        super().__init__(
            name="NewsletterSendProcessor",
            description="Sends newsletter to all active subscribers",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Send newsletter to all active subscribers.

        Args:
            entity: The Newsletter entity to process
            **kwargs: Additional processing parameters

        Returns:
            The newsletter entity with updated send counts
        """
        try:
            self.logger.info(
                f"Sending newsletter {getattr(entity, 'technical_id', '<unknown>')}"
            )

            newsletter = cast_entity(entity, Newsletter)

            service = get_entity_service()
            subscribers = await service.find_all(
                entity_class=Subscriber.ENTITY_NAME,
                entity_version=str(Subscriber.ENTITY_VERSION),
            )

            sent_count = 0
            failed_count = 0

            for subscriber_response in subscribers:
                subscriber = cast_entity(subscriber_response.data, Subscriber)
                if subscriber.is_active():
                    try:
                        await self._send_email(subscriber.email, newsletter.cat_fact)
                        sent_count += 1
                        self.logger.info(f"Email sent to {subscriber.email}")
                    except Exception as e:
                        failed_count += 1
                        self.logger.error(
                            f"Failed to send email to {subscriber.email}: {str(e)}"
                        )

            newsletter.sent_count = sent_count
            newsletter.failed_count = failed_count
            newsletter.mark_sent()

            self.logger.info(
                f"Newsletter {newsletter.technical_id} sent to {sent_count} subscribers, {failed_count} failures"
            )

            return newsletter

        except Exception as e:
            self.logger.error(
                f"Error sending newsletter {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _send_email(self, email: str, cat_fact: str) -> None:
        """
        Send an email to a subscriber.

        Args:
            email: The subscriber's email address
            cat_fact: The cat fact content to send

        Raises:
            Exception: If email sending fails
        """
        # Placeholder for email sending logic
        # In a real application, this would use an email service like SendGrid, AWS SES, etc.
        self.logger.debug(f"Sending email to {email} with cat fact: {cat_fact[:50]}...")
