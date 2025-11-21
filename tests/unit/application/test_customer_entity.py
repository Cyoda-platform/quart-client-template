"""
Unit tests for Customer entity validation and business logic.
"""

import pytest
from pydantic import ValidationError

from application.entity.customer.version_1.customer import Customer


class TestCustomerEntity:
    """Test Customer entity validation and business logic."""

    def test_customer_creation_valid(self):
        """Test creating a valid customer."""
        customer = Customer(
            name="John Doe",
            email="john.doe@example.com",
            phone="+1-555-123-4567",
            address="123 Main St, Anytown, USA"
        )
        
        assert customer.name == "John Doe"
        assert customer.email == "john.doe@example.com"
        assert customer.phone == "+1-555-123-4567"
        assert customer.address == "123 Main St, Anytown, USA"
        assert customer.state == "initial_state"

    def test_customer_creation_minimal(self):
        """Test creating a customer with only required fields."""
        customer = Customer(
            name="Jane Smith",
            email="jane.smith@example.com"
        )
        
        assert customer.name == "Jane Smith"
        assert customer.email == "jane.smith@example.com"
        assert customer.phone is None
        assert customer.address is None

    def test_customer_name_validation(self):
        """Test customer name validation."""
        # Test empty name
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="", email="test@example.com")
        assert "Name must be non-empty" in str(exc_info.value)

        # Test short name
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="A", email="test@example.com")
        assert "Name must be at least 2 characters long" in str(exc_info.value)

        # Test long name
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="A" * 101, email="test@example.com")
        assert "Name must be at most 100 characters long" in str(exc_info.value)

    def test_customer_email_validation(self):
        """Test customer email validation."""
        # Test empty email
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="John Doe", email="")
        assert "Email must be non-empty" in str(exc_info.value)

        # Test invalid email format
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="John Doe", email="invalid-email")
        assert "Email must be a valid email address" in str(exc_info.value)

        # Test email too long
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="John Doe", email="a" * 250 + "@example.com")
        assert "Email must be at most 255 characters long" in str(exc_info.value)

        # Test valid email normalization
        customer = Customer(name="John Doe", email="John.Doe@EXAMPLE.COM")
        assert customer.email == "john.doe@example.com"

    def test_customer_phone_validation(self):
        """Test customer phone validation."""
        # Test valid phone formats
        valid_phones = [
            "+1-555-123-4567",
            "(555) 123-4567",
            "555.123.4567",
            "5551234567",
            "+44 20 7946 0958"
        ]
        
        for phone in valid_phones:
            customer = Customer(name="John Doe", email="john@example.com", phone=phone)
            assert customer.phone == phone

        # Test invalid phone format
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="John Doe", email="john@example.com", phone="invalid-phone!")
        assert "Phone must contain only digits, spaces, hyphens, parentheses, and plus signs" in str(exc_info.value)

        # Test phone too long
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="John Doe", email="john@example.com", phone="1" * 21)
        assert "Phone must be at most 20 characters long" in str(exc_info.value)

        # Test empty phone becomes None
        customer = Customer(name="John Doe", email="john@example.com", phone="")
        assert customer.phone is None

    def test_customer_address_validation(self):
        """Test customer address validation."""
        # Test valid address
        customer = Customer(
            name="John Doe", 
            email="john@example.com", 
            address="123 Main St, Anytown, USA"
        )
        assert customer.address == "123 Main St, Anytown, USA"

        # Test address too long
        with pytest.raises(ValidationError) as exc_info:
            Customer(
                name="John Doe", 
                email="john@example.com", 
                address="A" * 501
            )
        assert "Address must be at most 500 characters long" in str(exc_info.value)

        # Test empty address becomes None
        customer = Customer(name="John Doe", email="john@example.com", address="")
        assert customer.address is None

    def test_customer_business_logic_validation(self):
        """Test customer business logic validation."""
        # Test missing required fields
        with pytest.raises(ValidationError) as exc_info:
            Customer(name="", email="")
        assert "Name and email are required fields" in str(exc_info.value)

    def test_customer_update_timestamp(self):
        """Test customer timestamp update functionality."""
        customer = Customer(name="John Doe", email="john@example.com")
        
        # Initially updated_at should be None
        assert customer.updated_at is None
        
        # Update timestamp
        customer.update_timestamp()
        assert customer.updated_at is not None

    def test_customer_processed_data(self):
        """Test customer processed data functionality."""
        customer = Customer(name="John Doe", email="john@example.com")
        
        processed_data = {"status": "processed", "score": 95}
        customer.set_processed_data(processed_data)
        
        assert customer.processed_data == processed_data
        assert customer.updated_at is not None

    def test_customer_validation_result(self):
        """Test customer validation result functionality."""
        customer = Customer(name="John Doe", email="john@example.com")
        
        validation_result = {"valid": True, "checks": ["email", "name"]}
        customer.set_validation_result(validation_result)
        
        assert customer.validation_result == validation_result
        assert customer.updated_at is not None

    def test_customer_workflow_state_checks(self):
        """Test customer workflow state check methods."""
        customer = Customer(name="John Doe", email="john@example.com")
        
        # Initial state
        assert not customer.is_ready_for_processing()
        assert not customer.is_processed()
        
        # Validated state
        customer.state = "validated"
        assert customer.is_ready_for_processing()
        assert not customer.is_processed()
        
        # Processed state
        customer.state = "processed"
        assert not customer.is_ready_for_processing()
        assert customer.is_processed()
        
        # Completed state
        customer.state = "completed"
        assert not customer.is_ready_for_processing()
        assert customer.is_processed()

    def test_customer_api_response(self):
        """Test customer API response conversion."""
        customer = Customer(
            name="John Doe",
            email="john@example.com",
            phone="+1-555-123-4567",
            address="123 Main St"
        )
        
        response = customer.to_api_response()
        
        assert response["name"] == "John Doe"
        assert response["email"] == "john@example.com"
        assert response["phone"] == "+1-555-123-4567"
        assert response["address"] == "123 Main St"
        assert response["state"] == "initial_state"
        assert "createdAt" in response
        assert "entity_id" in response
