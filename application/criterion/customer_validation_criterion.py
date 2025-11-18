"""
CustomerValidationCriterion for Cyoda Client Application

Validates that a Customer meets all required business rules before it can
proceed to the activation stage as specified in customer management requirements.
"""

import re
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.customer.version_1.customer import Customer


class CustomerValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Customer that checks all business rules
    before the customer can proceed to activation stage.
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

            # Validate required fields
            if not self._validate_name(customer):
                return False

            if not self._validate_email(customer):
                return False

            if not self._validate_phone(customer):
                return False

            if not self._validate_address(customer):
                return False

            if not self._validate_customer_type(customer):
                return False

            # Validate business logic rules
            if not self._validate_business_rules(customer):
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

    def _validate_name(self, customer: Customer) -> bool:
        """Validate customer name field"""
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

        return True

    def _validate_email(self, customer: Customer) -> bool:
        """Validate customer email field"""
        if not customer.email:
            self.logger.warning(
                f"Customer {customer.technical_id} has missing email"
            )
            return False

        # Basic email validation (Pydantic EmailStr already validates format)
        email_str = str(customer.email)
        if len(email_str) > 254:  # RFC 5321 limit
            self.logger.warning(
                f"Customer {customer.technical_id} email too long: {len(email_str)} characters"
            )
            return False

        return True

    def _validate_phone(self, customer: Customer) -> bool:
        """Validate customer phone field"""
        if not customer.phone or len(customer.phone.strip()) == 0:
            self.logger.warning(
                f"Customer {customer.technical_id} has missing phone number"
            )
            return False

        # Remove common phone formatting characters
        phone_clean = re.sub(r'[^\d+]', '', customer.phone)
        
        if len(phone_clean) < 10:
            self.logger.warning(
                f"Customer {customer.technical_id} phone number too short: '{customer.phone}'"
            )
            return False

        if len(phone_clean) > 15:
            self.logger.warning(
                f"Customer {customer.technical_id} phone number too long: '{customer.phone}'"
            )
            return False

        return True

    def _validate_address(self, customer: Customer) -> bool:
        """Validate customer address fields"""
        if not customer.address_line1 or len(customer.address_line1.strip()) == 0:
            self.logger.warning(
                f"Customer {customer.technical_id} has missing address line 1"
            )
            return False

        if not customer.city or len(customer.city.strip()) == 0:
            self.logger.warning(
                f"Customer {customer.technical_id} has missing city"
            )
            return False

        if not customer.postal_code or len(customer.postal_code.strip()) == 0:
            self.logger.warning(
                f"Customer {customer.technical_id} has missing postal code"
            )
            return False

        if not customer.country or len(customer.country.strip()) == 0:
            self.logger.warning(
                f"Customer {customer.technical_id} has missing country"
            )
            return False

        return True

    def _validate_customer_type(self, customer: Customer) -> bool:
        """Validate customer type field"""
        allowed_types = ["INDIVIDUAL", "BUSINESS", "PREMIUM", "CORPORATE"]
        if customer.customer_type not in allowed_types:
            self.logger.warning(
                f"Customer {customer.technical_id} has invalid customer type: {customer.customer_type}"
            )
            return False

        return True

    def _validate_business_rules(self, customer: Customer) -> bool:
        """Validate business logic rules"""
        # Premium customers must be active
        if customer.customer_type == "PREMIUM" and not customer.is_active:
            self.logger.warning(
                f"Customer {customer.technical_id} PREMIUM customers must be active"
            )
            return False

        # Corporate customers should have business-appropriate email domains
        if customer.customer_type == "CORPORATE":
            email_str = str(customer.email)
            if email_str.endswith(('@gmail.com', '@yahoo.com', '@hotmail.com', '@outlook.com')):
                self.logger.warning(
                    f"Customer {customer.technical_id} CORPORATE customer has personal email domain"
                )
                # This is a warning, not a failure - allow it but log it
                pass

        return True
