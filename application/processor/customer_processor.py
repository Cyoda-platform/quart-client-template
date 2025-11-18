"""
CustomerProcessor for Cyoda Client Application

Handles the main business logic for processing Customer instances.
It enriches the customer data and performs basic customer processing
operations.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.customer.version_1.customer import Customer
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class CustomerProcessor(CyodaProcessor):
    """
    Processor for Customer that handles main business logic,
    enriches customer data, and performs customer-specific operations.
    """

    def __init__(self) -> None:
        super().__init__(
            name="CustomerProcessor",
            description="Processes Customer instances and enriches customer data",
        )
        # Ensure logger attribute is present for type-checkers/readers.
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Customer according to business requirements.

        Args:
            entity: The Customer to process (must be in 'active' state)
            **kwargs: Additional processing parameters

        Returns:
            The processed customer with enriched data
        """
        try:
            self.logger.info(
                f"Processing Customer {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Customer for type-safe operations
            customer = cast_entity(entity, Customer)

            # Enrich customer with processed data
            processed_data = self._create_processed_data(customer)
            customer.add_metadata("processed_data", processed_data)

            # Perform customer-specific processing
            await self._perform_customer_processing(customer)

            # Log processing completion
            self.logger.info(f"Customer {customer.technical_id} processed successfully")

            return customer

        except Exception as e:
            self.logger.error(
                f"Error processing customer {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _create_processed_data(self, customer: Customer) -> Dict[str, Any]:
        """
        Create processed data for the customer.

        Args:
            customer: The Customer to process

        Returns:
            Dictionary containing processed data
        """
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        # Create processed data
        processed_data: Dict[str, Any] = {
            "processed_at": current_timestamp,
            "customer_status": "PROCESSED",
            "email_domain": (
                customer.email.split("@")[1] if "@" in customer.email else "unknown"
            ),
            "name_length": len(customer.name),
            "phone_digits": len([c for c in customer.phone if c.isdigit()]),
        }

        return processed_data

    async def _perform_customer_processing(self, customer: Customer) -> None:
        """
        Perform customer-specific processing operations.

        Args:
            customer: The processed Customer
        """
        try:
            # Add customer processing timestamp to metadata
            customer.add_metadata(
                "last_processed",
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )

            # Add customer tier based on email domain (simple business logic)
            email_domain = (
                customer.email.split("@")[1] if "@" in customer.email else "unknown"
            )
            if email_domain in ["gmail.com", "yahoo.com", "hotmail.com"]:
                customer_tier = "STANDARD"
            elif email_domain.endswith(".edu"):
                customer_tier = "ACADEMIC"
            elif email_domain.endswith(".gov"):
                customer_tier = "GOVERNMENT"
            else:
                customer_tier = "PREMIUM"

            customer.add_metadata("customer_tier", customer_tier)

            self.logger.info(
                f"Customer {customer.technical_id} assigned tier: {customer_tier}"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to perform customer processing for Customer {customer.technical_id}: {str(e)}"
            )
            # Continue processing even if this fails
            pass
