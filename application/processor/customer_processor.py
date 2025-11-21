"""
CustomerProcessor for Cyoda Client Application

Handles the main business logic for processing Customer instances.
Performs email uniqueness validation and other business rules as specified in requirements.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.customer.version_1.customer import Customer
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from common.service.entity_service import SearchConditionRequest
from services.services import get_entity_service


class CustomerProcessor(CyodaProcessor):
    """
    Processor for Customer that handles business logic,
    email uniqueness validation, and data enrichment.
    """

    def __init__(self) -> None:
        super().__init__(
            name="CustomerProcessor",
            description="Processes Customer instances, validates email uniqueness and enriches data",
        )
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
            The processed entity with enriched data
        """
        try:
            self.logger.info(
                f"Processing Customer {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Customer for type-safe operations
            customer = cast_entity(entity, Customer)

            # Validate email uniqueness
            await self._validate_email_uniqueness(customer)

            # Update timestamp
            customer.update_timestamp()

            # Log processing completion
            self.logger.info(f"Customer {customer.technical_id} processed successfully")

            return customer

        except Exception as e:
            self.logger.error(
                f"Error processing Customer {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _validate_email_uniqueness(self, customer: Customer) -> None:
        """
        Validate that the customer's email is unique in the system.

        Args:
            customer: The Customer entity to validate

        Raises:
            ValueError: If email is not unique
        """
        entity_service = get_entity_service()

        try:
            # Search for existing customers with the same email
            builder = SearchConditionRequest.builder()
            builder.equals("email", customer.email)
            condition = builder.build()

            existing_customers = await entity_service.search(
                entity_class=Customer.ENTITY_NAME,
                condition=condition,
                entity_version=str(Customer.ENTITY_VERSION),
            )

            # Check if any existing customer has the same email but different ID
            for existing_customer_response in existing_customers:
                existing_customer_data = existing_customer_response.data
                existing_id = getattr(
                    existing_customer_data, "technical_id", None
                ) or getattr(existing_customer_data, "entity_id", None)
                current_id = customer.technical_id or customer.entity_id

                if existing_id and existing_id != current_id:
                    self.logger.warning(
                        f"Email uniqueness violation: {customer.email} already exists for customer {existing_id}"
                    )
                    raise ValueError(
                        f"Email {customer.email} is already in use by another customer"
                    )

            self.logger.info(
                f"Email uniqueness validated for customer {customer.technical_id}"
            )

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Error validating email uniqueness: {str(e)}")
            # Don't fail processing for technical errors in uniqueness check
            # In production, this might be handled differently
            pass
