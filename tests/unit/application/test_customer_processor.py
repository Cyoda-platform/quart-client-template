"""
Unit tests for Customer processor business logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from application.entity.customer.version_1.customer import Customer
from application.processor.customer_processor import CustomerProcessor
from common.entity.cyoda_entity import CyodaEntity


class TestCustomerProcessor:
    """Test Customer processor business logic."""

    @pytest.fixture
    def processor(self):
        """Create a CustomerProcessor instance for testing."""
        return CustomerProcessor()

    @pytest.fixture
    def sample_customer(self):
        """Create a sample customer for testing."""
        return Customer(
            name="John Doe",
            email="john.doe@example.com",
            phone="+1-555-123-4567",
            address="123 Main St, Anytown, USA"
        )

    @pytest.mark.asyncio
    async def test_process_customer_success(self, processor, sample_customer):
        """Test successful customer processing."""
        # Set customer to validated state
        sample_customer.state = "validated"
        
        # Process the customer
        result = await processor.process(sample_customer)
        
        # Verify the result
        assert isinstance(result, Customer)
        assert result.processed_data is not None
        assert result.processed_data["processing_status"] == "COMPLETED"
        assert result.processed_data["customer_type"] in ["PREMIUM", "STANDARD", "BASIC"]
        assert result.processed_data["email_domain"] == "example.com"
        assert result.processed_data["has_phone"] is True
        assert result.processed_data["has_address"] is True
        assert "processed_at" in result.processed_data
        assert "processing_id" in result.processed_data

    @pytest.mark.asyncio
    async def test_process_customer_minimal_data(self, processor):
        """Test processing customer with minimal data."""
        customer = Customer(
            name="Jane Smith",
            email="jane@example.com"
        )
        customer.state = "validated"
        
        result = await processor.process(customer)
        
        assert result.processed_data["customer_type"] == "BASIC"
        assert result.processed_data["email_domain"] == "example.com"
        assert result.processed_data["has_phone"] is False
        assert result.processed_data["has_address"] is False

    @pytest.mark.asyncio
    async def test_process_customer_with_phone_only(self, processor):
        """Test processing customer with phone but no address."""
        customer = Customer(
            name="Bob Johnson",
            email="bob@example.com",
            phone="+1-555-987-6543"
        )
        customer.state = "validated"
        
        result = await processor.process(customer)
        
        assert result.processed_data["customer_type"] == "STANDARD"
        assert result.processed_data["has_phone"] is True
        assert result.processed_data["has_address"] is False

    @pytest.mark.asyncio
    async def test_process_customer_with_address_only(self, processor):
        """Test processing customer with address but no phone."""
        customer = Customer(
            name="Alice Brown",
            email="alice@example.com",
            address="456 Oak Ave"
        )
        customer.state = "validated"
        
        result = await processor.process(customer)
        
        assert result.processed_data["customer_type"] == "STANDARD"
        assert result.processed_data["has_phone"] is False
        assert result.processed_data["has_address"] is True

    @pytest.mark.asyncio
    async def test_process_customer_error_handling(self, processor):
        """Test error handling in customer processing."""
        # Create an invalid entity (not a Customer)
        invalid_entity = CyodaEntity()
        
        with pytest.raises(Exception):
            await processor.process(invalid_entity)

    def test_determine_customer_type_premium(self, processor):
        """Test customer type determination for premium customers."""
        customer = Customer(
            name="Premium Customer",
            email="premium@example.com",
            phone="+1-555-123-4567",
            address="123 Premium St"
        )
        
        customer_type = processor._determine_customer_type(customer)
        assert customer_type == "PREMIUM"

    def test_determine_customer_type_standard_with_phone(self, processor):
        """Test customer type determination for standard customers with phone."""
        customer = Customer(
            name="Standard Customer",
            email="standard@example.com",
            phone="+1-555-123-4567"
        )
        
        customer_type = processor._determine_customer_type(customer)
        assert customer_type == "STANDARD"

    def test_determine_customer_type_standard_with_address(self, processor):
        """Test customer type determination for standard customers with address."""
        customer = Customer(
            name="Standard Customer",
            email="standard@example.com",
            address="123 Standard St"
        )
        
        customer_type = processor._determine_customer_type(customer)
        assert customer_type == "STANDARD"

    def test_determine_customer_type_basic(self, processor):
        """Test customer type determination for basic customers."""
        customer = Customer(
            name="Basic Customer",
            email="basic@example.com"
        )
        
        customer_type = processor._determine_customer_type(customer)
        assert customer_type == "BASIC"

    def test_create_processed_data(self, processor, sample_customer):
        """Test processed data creation."""
        processed_data = processor._create_processed_data(sample_customer)
        
        assert processed_data["processing_status"] == "COMPLETED"
        assert processed_data["customer_type"] == "PREMIUM"
        assert processed_data["email_domain"] == "example.com"
        assert processed_data["has_phone"] is True
        assert processed_data["has_address"] is True
        assert "processed_at" in processed_data
        assert "processing_id" in processed_data

    def test_processor_initialization(self, processor):
        """Test processor initialization."""
        assert processor.name == "CustomerProcessor"
        assert "Processes Customer instances" in processor.description
        assert hasattr(processor, 'logger')
