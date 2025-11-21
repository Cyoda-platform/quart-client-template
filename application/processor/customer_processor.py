"""
CustomerProcessor for Cyoda Client Application

Handles the main business logic for processing Customer instances.
It enriches the customer data and performs basic processing operations
as specified in functional requirements.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.customer.version_1.customer import Customer
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class CustomerProcessor(CyodaProcessor):
    """
    Processor for Customer that handles main business logic,
    enriches customer data, and performs basic processing operations.
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
        Process the Customer according to functional requirements.

        Args:
            entity: The Customer to process (must be in 'validated' state)
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
            customer.processed_data = processed_data

            # Update timestamp
            customer.update_timestamp()

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
        Create processed data according to functional requirements.

        Args:
            customer: The Customer to process

        Returns:
            Dictionary containing processed data
        """
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        processing_id = str(uuid.uuid4())

        # Create processed data with customer enrichment
        processed_data: Dict[str, Any] = {
            "processed_at": current_timestamp,
            "processing_id": processing_id,
            "processing_status": "COMPLETED",
            "customer_type": self._determine_customer_type(customer),
            "email_domain": customer.email.split("@")[1] if customer.email else None,
            "has_phone": customer.phone is not None and len(customer.phone.strip()) > 0,
            "has_address": customer.address is not None
            and len(customer.address.strip()) > 0,
        }

        return processed_data

    def _determine_customer_type(self, customer: Customer) -> str:
        """
        Determine customer type based on business rules.

        Args:
            customer: The Customer entity

        Returns:
            Customer type: PREMIUM, STANDARD, or BASIC
        """
        # Simple business logic for customer classification
        if customer.phone and customer.address:
            return "PREMIUM"
        elif customer.phone or customer.address:
            return "STANDARD"
        else:
            return "BASIC"
