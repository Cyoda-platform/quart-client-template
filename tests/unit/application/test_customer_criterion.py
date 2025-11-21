"""
Unit tests for Customer validation criterion.
"""

import pytest
from unittest.mock import MagicMock

from application.criterion.customer_validation_criterion import CustomerValidationCriterion
from application.entity.customer.version_1.customer import Customer
from common.entity.cyoda_entity import CyodaEntity


class TestCustomerValidationCriterion:
    """Test Customer validation criterion business logic."""

    @pytest.fixture
    def criterion(self):
        """Create a CustomerValidationCriterion instance for testing."""
        return CustomerValidationCriterion()

    @pytest.fixture
    def valid_customer(self):
        """Create a valid customer for testing."""
        return Customer(
            name="John Doe",
            email="john.doe@example.com",
            phone="+1-555-123-4567",
            address="123 Main St, Anytown, USA"
        )

    @pytest.mark.asyncio
    async def test_check_valid_customer(self, criterion, valid_customer):
        """Test validation of a valid customer."""
        result = await criterion.check(valid_customer)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_valid_customer_minimal(self, criterion):
        """Test validation of a customer with minimal valid data."""
        customer = Customer(
            name="Jane Smith",
            email="jane@example.com"
        )
        
        result = await criterion.check(customer)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_criterion_logic_directly(self, criterion):
        """Test the criterion validation logic directly."""
        # Since Pydantic validates at creation time, we test the criterion logic
        # by creating a mock customer object with the attributes we want to test

        class MockCustomer:
            def __init__(self, name, email, phone=None, address=None):
                self.name = name
                self.email = email
                self.phone = phone
                self.address = address
                self.technical_id = "test-id"

        # Test invalid name cases
        mock_customer = MockCustomer("", "test@example.com")
        result = await criterion.check(mock_customer)
        assert result is False

        mock_customer = MockCustomer("A", "test@example.com")
        result = await criterion.check(mock_customer)
        assert result is False

        mock_customer = MockCustomer("A" * 101, "test@example.com")
        result = await criterion.check(mock_customer)
        assert result is False

        # Test invalid email cases
        mock_customer = MockCustomer("John Doe", "")
        result = await criterion.check(mock_customer)
        assert result is False

        mock_customer = MockCustomer("John Doe", "invalid-email")
        result = await criterion.check(mock_customer)
        assert result is False

        mock_customer = MockCustomer("John Doe", "a" * 250 + "@example.com")
        result = await criterion.check(mock_customer)
        assert result is False

        # Test invalid phone cases
        mock_customer = MockCustomer("John Doe", "john@example.com", "invalid-phone!")
        result = await criterion.check(mock_customer)
        assert result is False

        mock_customer = MockCustomer("John Doe", "john@example.com", "1" * 21)
        result = await criterion.check(mock_customer)
        assert result is False

        # Test invalid address case
        mock_customer = MockCustomer("John Doe", "john@example.com", None, "A" * 501)
        result = await criterion.check(mock_customer)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_valid_phone_formats(self, criterion):
        """Test validation passes for various valid phone formats."""
        valid_phones = [
            "+1-555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "5551234567",
            "+44 20 7946 0958"
        ]
        
        for phone in valid_phones:
            customer = Customer(
                name="John Doe",
                email="john@example.com",
                phone=phone
            )
            
            result = await criterion.check(customer)
            assert result is True, f"Phone format {phone} should be valid"

    @pytest.mark.asyncio
    async def test_check_none_phone_and_address(self, criterion):
        """Test validation passes for None phone and address."""
        customer = Customer(
            name="John Doe",
            email="john@example.com",
            phone=None,
            address=None
        )
        
        result = await criterion.check(customer)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_error_handling(self, criterion):
        """Test error handling in validation."""
        # Create an invalid entity (not a Customer)
        invalid_entity = CyodaEntity()
        
        result = await criterion.check(invalid_entity)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_exception_handling(self, criterion, valid_customer):
        """Test exception handling during validation."""
        # Test with invalid entity type - should return False, not raise exception
        result = await criterion.check("not_an_entity")
        assert result is False

    def test_criterion_initialization(self, criterion):
        """Test criterion initialization."""
        assert criterion.name == "CustomerValidationCriterion"
        assert "Validates Customer business rules" in criterion.description
        assert hasattr(criterion, 'logger')
