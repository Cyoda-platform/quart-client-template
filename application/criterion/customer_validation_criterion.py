"""
CustomerValidationCriterion for Cyoda Client Application

Validates that a Customer meets all required business rules before it can
proceed to the processing stage as specified in functional requirements.
"""

import re
from typing import Any

from application.entity.customer.version_1.customer import Customer
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class CustomerValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Customer that checks all business rules
    before the entity can proceed to processing stage.
    """

    def __init__(self) -> None:
        super().__init__(
            name="CustomerValidationCriterion",
            description="Validates Customer business rules and data consistency",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the entity meets all validation criteria.

        Args:
            entity: The CyodaEntity to validate (expected to be Customer)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity meets all criteria, False otherwise
        """
        try:
            self.logger.info(
                f"Validating Customer {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Customer for type-safe operations
            customer = cast_entity(entity, Customer)

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
                    f"Customer {customer.technical_id} has missing email"
                )
                return False

            # Email format validation
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
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
                phone_clean = re.sub(r"[^\d+\-\(\)\s]", "", customer.phone.strip())
                if len(phone_clean) < 10:
                    self.logger.warning(
                        f"Customer {customer.technical_id} has invalid phone: too short"
                    )
                    return False
                if len(phone_clean) > 20:
                    self.logger.warning(
                        f"Customer {customer.technical_id} has invalid phone: too long"
                    )
                    return False

            # Validate address fields if address is provided
            if customer.address is not None:
                if customer.address.street and len(customer.address.street) > 255:
                    self.logger.warning(
                        f"Customer {customer.technical_id} has invalid address street: too long"
                    )
                    return False

                if customer.address.city and len(customer.address.city) > 100:
                    self.logger.warning(
                        f"Customer {customer.technical_id} has invalid address city: too long"
                    )
                    return False

                if customer.address.state and len(customer.address.state) > 100:
                    self.logger.warning(
                        f"Customer {customer.technical_id} has invalid address state: too long"
                    )
                    return False

                if customer.address.zip and len(customer.address.zip) > 20:
                    self.logger.warning(
                        f"Customer {customer.technical_id} has invalid address zip: too long"
                    )
                    return False

            self.logger.info(
                f"Customer {customer.technical_id} passed all validation criteria"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Error validating Customer {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
