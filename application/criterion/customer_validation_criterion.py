"""
CustomerValidationCriterion for Cyoda Client Application

Validates that a Customer meets all required business rules before it can
proceed to the processing stage. Ensures data quality and business rule compliance.
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

            # Validate customer_id
            if not self._validate_customer_id(customer):
                return False

            # Validate name
            if not self._validate_name(customer):
                return False

            # Validate email
            if not self._validate_email(customer):
                return False

            # Validate phone
            if not self._validate_phone(customer):
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
                f"Error validating customer "
                f"{getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

    def _validate_customer_id(self, customer: Customer) -> bool:
        """Validate customer_id field"""
        if not customer.customer_id or len(customer.customer_id.strip()) == 0:
            self.logger.warning(
                f"Customer {customer.technical_id} has empty customer_id"
            )
            return False

        if len(customer.customer_id) < 3:
            self.logger.warning(
                f"Customer {customer.technical_id} has customer_id too short: "
                f"'{customer.customer_id}'"
            )
            return False

        if len(customer.customer_id) > 50:
            self.logger.warning(
                f"Customer {customer.technical_id} has customer_id too long: "
                f"'{customer.customer_id}'"
            )
            return False

        return True

    def _validate_name(self, customer: Customer) -> bool:
        """Validate name field"""
        if not customer.name or len(customer.name.strip()) == 0:
            self.logger.warning(f"Customer {customer.technical_id} has empty name")
            return False

        if len(customer.name) < 2:
            self.logger.warning(
                f"Customer {customer.technical_id} has name too short: "
                f"'{customer.name}'"
            )
            return False

        if len(customer.name) > 100:
            self.logger.warning(
                f"Customer {customer.technical_id} has name too long: "
                f"'{customer.name}'"
            )
            return False

        return True

    def _validate_email(self, customer: Customer) -> bool:
        """Validate email field"""
        if not customer.email or len(customer.email.strip()) == 0:
            self.logger.warning(f"Customer {customer.technical_id} has empty email")
            return False

        # Basic email validation using regex
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, customer.email.strip()):
            self.logger.warning(
                f"Customer {customer.technical_id} has invalid email format: "
                f"'{customer.email}'"
            )
            return False

        if len(customer.email) > 255:
            self.logger.warning(
                f"Customer {customer.technical_id} has email too long: "
                f"'{customer.email}'"
            )
            return False

        return True

    def _validate_phone(self, customer: Customer) -> bool:
        """Validate phone field"""
        if not customer.phone or len(customer.phone.strip()) == 0:
            self.logger.warning(f"Customer {customer.technical_id} has empty phone")
            return False

        # Remove common phone number separators for validation
        cleaned_phone = re.sub(r"[\s\-\(\)\+\.]", "", customer.phone.strip())

        # Check if it contains only digits after cleaning
        if not cleaned_phone.isdigit():
            self.logger.warning(
                f"Customer {customer.technical_id} has invalid phone format: "
                f"'{customer.phone}'"
            )
            return False

        if len(cleaned_phone) < 10:
            self.logger.warning(
                f"Customer {customer.technical_id} has phone too short: "
                f"'{customer.phone}'"
            )
            return False

        if len(cleaned_phone) > 15:
            self.logger.warning(
                f"Customer {customer.technical_id} has phone too long: "
                f"'{customer.phone}'"
            )
            return False

        return True

    def _validate_business_rules(self, customer: Customer) -> bool:
        """Validate business logic rules"""
        # Example business rule: email domain validation for business customers
        if customer.email:
            email_domain = (
                customer.email.split("@")[1].lower() if "@" in customer.email else ""
            )

            # Business domains should have proper business email format
            business_domains = [
                "company.com",
                "corp.com",
                "business.com",
                "enterprise.com",
            ]
            if any(domain in email_domain for domain in business_domains):
                # Business customers should have more formal names
                if len(customer.name.split()) < 2:
                    self.logger.warning(
                        f"Customer {customer.technical_id} with business email "
                        f"should have full name: '{customer.name}'"
                    )
                    return False

        # Example business rule: active customers should have complete contact info
        if customer.is_active:
            if not customer.email or not customer.phone:
                self.logger.warning(
                    f"Customer {customer.technical_id} is active but missing "
                    f"contact information"
                )
                return False

        return True
