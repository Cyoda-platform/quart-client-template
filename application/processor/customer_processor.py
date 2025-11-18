"""
CustomerProcessor for Cyoda Client Application

Handles the main business logic for processing Customer instances.
It enriches the customer data, performs validation, and updates
customer status as specified in the customer management requirements.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.customer.version_1.customer import Customer
from services.services import get_entity_service


class CustomerProcessor(CyodaProcessor):
    """
    Processor for Customer that handles main business logic,
    enriches customer data, and performs customer activation processing.
    """

    def __init__(self) -> None:
        super().__init__(
            name="CustomerProcessor",
            description="Processes Customer instances, enriches data and performs customer activation",
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
            enriched_data = self._create_enriched_data(customer)
            customer.enriched_data = enriched_data

            # Perform customer activation logic
            await self._perform_customer_activation(customer)

            # Update customer status
            customer.update_timestamp()

            # Log processing completion
            self.logger.info(
                f"Customer {customer.technical_id} processed successfully"
            )

            return customer

        except Exception as e:
            self.logger.error(
                f"Error processing customer {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _create_enriched_data(self, customer: Customer) -> Dict[str, Any]:
        """
        Create enriched data for the customer.

        Args:
            customer: The Customer to enrich

        Returns:
            Dictionary containing enriched customer data
        """
        current_timestamp = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        processing_id = str(uuid.uuid4())

        # Create enriched data based on customer information
        enriched_data: Dict[str, Any] = {
            "processed_at": current_timestamp,
            "processing_id": processing_id,
            "customer_segment": self._determine_customer_segment(customer),
            "risk_level": self._assess_risk_level(customer),
            "activation_status": "ACTIVATED",
            "full_address": customer.get_full_address(),
            "account_tier": self._determine_account_tier(customer),
        }

        return enriched_data

    async def _perform_customer_activation(self, customer: Customer) -> None:
        """
        Perform customer activation logic.

        Args:
            customer: The customer to activate
        """
        entity_service = get_entity_service()

        try:
            # Log customer activation
            self.logger.info(
                f"Activating customer {customer.name} (ID: {customer.technical_id})"
            )

            # Set customer as active if not already
            if not customer.is_active:
                customer.is_active = True
                self.logger.info(f"Customer {customer.technical_id} status set to active")

            # Additional activation logic could be added here
            # For example: sending welcome emails, creating accounts, etc.

        except Exception as e:
            self.logger.error(
                f"Failed to activate customer {customer.technical_id}: {str(e)}"
            )
            raise

    def _determine_customer_segment(self, customer: Customer) -> str:
        """
        Determine customer segment based on customer type and other factors.

        Args:
            customer: The Customer to segment

        Returns:
            Customer segment: STANDARD, BUSINESS, PREMIUM, or VIP
        """
        customer_type = customer.customer_type

        if customer_type == "PREMIUM":
            return "VIP"
        elif customer_type == "CORPORATE":
            return "BUSINESS"
        elif customer_type == "BUSINESS":
            return "BUSINESS"
        else:
            return "STANDARD"

    def _assess_risk_level(self, customer: Customer) -> str:
        """
        Assess risk level for the customer.

        Args:
            customer: The Customer to assess

        Returns:
            Risk level: LOW, MEDIUM, or HIGH
        """
        # Simple risk assessment based on customer type and status
        if customer.customer_type in ["PREMIUM", "CORPORATE"]:
            return "LOW"
        elif customer.customer_type == "BUSINESS":
            return "MEDIUM"
        else:
            return "LOW"  # Default to low risk for individual customers

    def _determine_account_tier(self, customer: Customer) -> str:
        """
        Determine account tier based on customer information.

        Args:
            customer: The Customer to evaluate

        Returns:
            Account tier: BASIC, STANDARD, PREMIUM, or ENTERPRISE
        """
        customer_type = customer.customer_type

        if customer_type == "PREMIUM":
            return "PREMIUM"
        elif customer_type == "CORPORATE":
            return "ENTERPRISE"
        elif customer_type == "BUSINESS":
            return "STANDARD"
        else:
            return "BASIC"
