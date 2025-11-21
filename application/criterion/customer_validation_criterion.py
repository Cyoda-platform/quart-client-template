"""
CustomerValidationCriterion for Cyoda Client Application

Validates that a Customer meets all required business rules before it can
proceed to the processing stage as specified in functional requirements.
"""

import re
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.customer.version_1.customer import Customer


class CustomerValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Customer that checks all business rules
    before the customer can proceed to processing stage.
    """

    def __init__(self) -> None:
        super().__init__(
            name="CustomerValidationCriterion",
            description="Validates Customer business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the customer meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Customer)
            **kwargs: Additional criteria parameters

        Returns:
            True if the customer meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating customer {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Customer for type-safe operations
            customer = cast_entity(entity, Customer)

            # State is managed by Cyoda workflow engine - no manual state checks needed

            # Validate required fields
            if not customer.name or len(customer.name.strip()) < 2:
                self.logger.warning(
                    f"Customer {customer.technical_id} has invalid name: '{customer.name}'"
                )
                return False

            if len(customer.name) > 100:
                self.logger.warning(
                    f"Customer {customer.technical_id} name too long: {len(customer.name)} characters"
                )
                return False

            # Validate email format and requirements
            if not customer.email or len(customer.email.strip()) == 0:
                self.logger.warning(
                    f"Customer {customer.technical_id} has empty email"
                )
                return False

            # Email format validation using regex
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, customer.email):
                self.logger.warning(
                    f"Customer {customer.technical_id} has invalid email format: {customer.email}"
                )
                return False

            if len(customer.email) > 255:
                self.logger.warning(
                    f"Customer {customer.technical_id} email too long: {len(customer.email)} characters"
                )
                return False

            # Validate phone if provided
            if customer.phone is not None and len(customer.phone.strip()) > 0:
                phone_pattern = r'^[\d\s\-\(\)\+\.]+$'
                if not re.match(phone_pattern, customer.phone):
                    self.logger.warning(
                        f"Customer {customer.technical_id} has invalid phone format: {customer.phone}"
                    )
                    return False

                if len(customer.phone) > 20:
                    self.logger.warning(
                        f"Customer {customer.technical_id} phone too long: {len(customer.phone)} characters"
                    )
                    return False

            # Validate address if provided
            if customer.address is not None and len(customer.address.strip()) > 0:
                if len(customer.address) > 500:
                    self.logger.warning(
                        f"Customer {customer.technical_id} address too long: {len(customer.address)} characters"
                    )
                    return False

            self.logger.info(
                f"Customer {customer.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating customer {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
