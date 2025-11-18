"""
CustomerProcessor for Cyoda Client Application

Handles the main business logic for processing Customer instances.
It enriches the customer data and performs basic customer processing
operations following the established patterns.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from application.entity.customer.version_1.customer import Customer
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class CustomerProcessor(CyodaProcessor):
    """
    Processor for Customer that handles main business logic,
    enriches customer data, and performs customer-specific processing.
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

            # Perform customer-specific processing
            await self._perform_customer_processing(customer)

            # Log processing completion
            self.logger.info(f"Customer {customer.technical_id} processed successfully")

            return customer

        except Exception as e:
            self.logger.error(
                f"Error processing customer "
                f"{getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
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
        processing_id = str(uuid.uuid4())

        # Create processed data with customer-specific enrichment
        processed_data: Dict[str, Any] = {
            "processed_at": current_timestamp,
            "processing_id": processing_id,
            "processing_status": "COMPLETED",
            "customer_type": self._determine_customer_type(customer),
            "contact_score": self._calculate_contact_score(customer),
            "enriched_name": customer.name.title(),  # Ensure proper capitalization
        }

        return processed_data

    async def _perform_customer_processing(self, customer: Customer) -> None:
        """
        Perform customer-specific processing operations.

        Args:
            customer: The processed Customer
        """
        try:
            # Example: Log customer processing for audit trail
            self.logger.info(
                f"Customer processing completed for {customer.name} "
                f"({customer.customer_id})"
            )

            # Additional customer-specific processing could be added here
            # For example: updating related entities, sending notifications, etc.

        except Exception as e:
            self.logger.error(
                f"Failed to complete customer processing for Customer "
                f"{customer.technical_id}: {str(e)}"
            )
            # Continue processing even if auxiliary operations fail
            pass

    def _determine_customer_type(self, customer: Customer) -> str:
        """
        Determine customer type based on business rules.

        Args:
            customer: The Customer entity

        Returns:
            Customer type: INDIVIDUAL, BUSINESS, or PREMIUM
        """
        # Simple business logic for customer type determination
        email_domain = (
            customer.email.split("@")[1].lower() if "@" in customer.email else ""
        )

        # Business domains (simplified list)
        business_domains = ["company.com", "corp.com", "business.com", "enterprise.com"]

        if any(domain in email_domain for domain in business_domains):
            return "BUSINESS"
        elif (
            customer.name.count(" ") >= 2
        ):  # Multiple names might indicate premium customer
            return "PREMIUM"
        else:
            return "INDIVIDUAL"

    def _calculate_contact_score(self, customer: Customer) -> int:
        """
        Calculate a contact completeness score for the customer.

        Args:
            customer: The Customer entity

        Returns:
            Contact score from 0-100
        """
        score = 0

        # Base score for having required fields
        score += 40  # Base score for having all required fields

        # Email quality score
        if "@" in customer.email and "." in customer.email.split("@")[1]:
            score += 20

        # Phone quality score
        cleaned_phone = (
            customer.phone.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )
        if len(cleaned_phone) >= 10:
            score += 20

        # Name quality score
        if len(customer.name.split()) >= 2:  # First and last name
            score += 10

        # Customer ID quality score
        if len(customer.customer_id) >= 5:  # Meaningful customer ID
            score += 10

        return min(score, 100)  # Cap at 100
