"""
Unit tests for Order processors.

Tests for OrderCreateProcessor, OrderUpdateProcessor, and OrderCancelProcessor
to ensure proper functionality, validation, and error handling.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from application.entity.order.version_1.order import Order
from application.processor.order.order_create_processor import OrderCreateProcessor
from application.processor.order.order_update_processor import OrderUpdateProcessor
from application.processor.order.order_cancel_processor import OrderCancelProcessor


class TestOrderCreateProcessor:
    """Test cases for OrderCreateProcessor."""

    @pytest.fixture
    def processor(self):
        """Create OrderCreateProcessor instance."""
        return OrderCreateProcessor()

    @pytest.fixture
    def sample_order(self):
        """Create sample Order entity."""
        return Order(
            customer_id="CUST123",
            amount=99.99,
            description="Test order"
        )

    @pytest.mark.asyncio
    async def test_process_order_creation_success(self, processor, sample_order):
        """Test successful order creation processing."""
        # Act
        result = await processor.process(sample_order)
        
        # Assert
        assert isinstance(result, Order)
        assert result.status == "created"
        assert result.created_at is not None
        assert result.processing_metadata is not None
        assert result.processing_metadata["processed_by"] == "OrderCreateProcessor"
        assert result.processing_metadata["transition"] == "create"
        assert result.processing_metadata["event_emitted"] == "OrderCreated"

    @pytest.mark.asyncio
    async def test_process_order_creation_sets_timestamps(self, processor, sample_order):
        """Test that order creation sets proper timestamps."""
        # Act
        result = await processor.process(sample_order)
        
        # Assert
        assert result.created_at is not None
        # Verify timestamp format (ISO 8601)
        datetime.fromisoformat(result.created_at.replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_process_order_creation_emits_event(self, processor, sample_order):
        """Test that order creation emits OrderCreated event."""
        with patch.object(processor, '_emit_order_created_event', new_callable=AsyncMock) as mock_emit:
            # Act
            await processor.process(sample_order)
            
            # Assert
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[0][0]
            assert isinstance(call_args, Order)
            assert call_args.status == "created"

    @pytest.mark.asyncio
    async def test_process_order_creation_handles_errors(self, processor, sample_order):
        """Test error handling in order creation."""
        with patch.object(processor, '_emit_order_created_event', side_effect=Exception("Event emission failed")):
            # Should not raise exception even if event emission fails
            result = await processor.process(sample_order)
            assert result.status == "created"


class TestOrderUpdateProcessor:
    """Test cases for OrderUpdateProcessor."""

    @pytest.fixture
    def processor(self):
        """Create OrderUpdateProcessor instance."""
        return OrderUpdateProcessor()

    @pytest.fixture
    def created_order(self):
        """Create Order entity in created status."""
        order = Order(
            customer_id="CUST123",
            amount=99.99,
            description="Test order"
        )
        order.set_status("created")
        return order

    @pytest.fixture
    def cancelled_order(self):
        """Create Order entity in cancelled status."""
        order = Order(
            customer_id="CUST123",
            amount=99.99,
            description="Test order"
        )
        order.set_status("cancelled")
        return order

    @pytest.mark.asyncio
    async def test_process_order_update_success(self, processor, created_order):
        """Test successful order update processing."""
        # Act
        result = await processor.process(created_order)
        
        # Assert
        assert isinstance(result, Order)
        assert result.status == "updated"
        assert result.updated_at is not None
        assert result.processing_metadata is not None
        assert result.processing_metadata["processed_by"] == "OrderUpdateProcessor"
        assert result.processing_metadata["transition"] == "update"
        assert result.processing_metadata["event_emitted"] == "OrderUpdated"

    @pytest.mark.asyncio
    async def test_process_order_update_sets_timestamps(self, processor, created_order):
        """Test that order update sets proper timestamps."""
        # Act
        result = await processor.process(created_order)
        
        # Assert
        assert result.updated_at is not None
        # Verify timestamp format (ISO 8601)
        datetime.fromisoformat(result.updated_at.replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_process_order_update_emits_event(self, processor, created_order):
        """Test that order update emits OrderUpdated event."""
        with patch.object(processor, '_emit_order_updated_event', new_callable=AsyncMock) as mock_emit:
            # Act
            await processor.process(created_order)
            
            # Assert
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args[0][0]
            assert isinstance(call_args, Order)
            assert call_args.status == "updated"

    @pytest.mark.asyncio
    async def test_process_order_update_cancelled_order_fails(self, processor, cancelled_order):
        """Test that updating a cancelled order fails."""
        # Act & Assert
        with pytest.raises(ValueError, match="cannot be updated"):
            await processor.process(cancelled_order)

    @pytest.mark.asyncio
    async def test_process_order_update_handles_errors(self, processor, created_order):
        """Test error handling in order update."""
        with patch.object(processor, '_emit_order_updated_event', side_effect=Exception("Event emission failed")):
            # Should not raise exception even if event emission fails
            result = await processor.process(created_order)
            assert result.status == "updated"


class TestOrderCancelProcessor:
    """Test cases for OrderCancelProcessor."""

    @pytest.fixture
    def processor(self):
        """Create OrderCancelProcessor instance."""
        return OrderCancelProcessor()

    @pytest.fixture
    def created_order(self):
        """Create Order entity in created status."""
        order = Order(
            customer_id="CUST123",
            amount=99.99,
            description="Test order"
        )
        order.set_status("created")
        return order

    @pytest.fixture
    def updated_order(self):
        """Create Order entity in updated status."""
        order = Order(
            customer_id="CUST123",
            amount=99.99,
            description="Test order"
        )
        order.set_status("updated")
        return order

    @pytest.fixture
    def cancelled_order(self):
        """Create Order entity in cancelled status."""
        order = Order(
            customer_id="CUST123",
            amount=99.99,
            description="Test order"
        )
        order.set_status("cancelled")
        return order

    @pytest.mark.asyncio
    async def test_process_order_cancellation_success(self, processor, created_order):
        """Test successful order cancellation processing."""
        with patch.object(processor, '_call_external_cancellation_service', return_value={"success": True}):
            # Act
            result = await processor.process(created_order)
            
            # Assert
            assert isinstance(result, Order)
            assert result.status == "cancelled"
            assert result.updated_at is not None
            assert result.processing_metadata is not None
            assert result.processing_metadata["processed_by"] == "OrderCancelProcessor"
            assert result.processing_metadata["transition"] == "cancel"
            assert result.processing_metadata["event_emitted"] == "OrderCancelled"

    @pytest.mark.asyncio
    async def test_process_order_cancellation_calls_external_service(self, processor, created_order):
        """Test that order cancellation calls external service."""
        with patch.object(processor, '_call_external_cancellation_service', new_callable=AsyncMock) as mock_service:
            mock_service.return_value = {"success": True, "cancellation_id": "CANCEL_123"}
            
            # Act
            await processor.process(created_order)
            
            # Assert
            mock_service.assert_called_once_with(created_order)

    @pytest.mark.asyncio
    async def test_process_order_cancellation_emits_event(self, processor, created_order):
        """Test that order cancellation emits OrderCancelled event."""
        with patch.object(processor, '_call_external_cancellation_service', return_value={"success": True}):
            with patch.object(processor, '_emit_order_cancelled_event', new_callable=AsyncMock) as mock_emit:
                # Act
                await processor.process(created_order)
                
                # Assert
                mock_emit.assert_called_once()
                call_args = mock_emit.call_args[0][0]
                assert isinstance(call_args, Order)
                assert call_args.status == "cancelled"

    @pytest.mark.asyncio
    async def test_process_order_cancellation_already_cancelled_fails(self, processor, cancelled_order):
        """Test that cancelling an already cancelled order fails."""
        # Act & Assert
        with pytest.raises(ValueError, match="cannot be cancelled"):
            await processor.process(cancelled_order)

    @pytest.mark.asyncio
    async def test_process_order_cancellation_external_service_failure(self, processor, created_order):
        """Test order cancellation with external service failure."""
        with patch.object(processor, '_call_external_cancellation_service', return_value={"success": False, "error": "Service unavailable"}):
            # Act
            result = await processor.process(created_order)
            
            # Assert - should still cancel the order even if external service fails
            assert result.status == "cancelled"
            assert result.processing_metadata["external_cancellation_result"]["success"] is False

    @pytest.mark.asyncio
    async def test_external_cancellation_service_success(self, processor, created_order):
        """Test external cancellation service call success."""
        # Act
        result = await processor._call_external_cancellation_service(created_order)
        
        # Assert
        assert result["success"] is True
        assert "cancellation_id" in result
        assert result["request_data"]["order_id"] == created_order.entity_id
        assert result["request_data"]["customer_id"] == created_order.customer_id

    @pytest.mark.asyncio
    async def test_external_cancellation_service_handles_errors(self, processor, created_order):
        """Test external cancellation service error handling."""
        with patch('application.utils.http_client.create_order_cancellation_client') as mock_client_factory:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client_factory.return_value = mock_client
            
            # Simulate HTTP client error
            from application.utils.http_client import HttpClientError
            mock_client.post.side_effect = HttpClientError("Connection failed")
            
            # Act
            result = await processor._call_external_cancellation_service(created_order)
            
            # Assert
            assert result["success"] is False
            assert "error" in result
            assert result["error_type"] == "unexpected_error"


# Integration test stubs for future implementation
class TestOrderProcessorsIntegration:
    """Integration test stubs for Order processors."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Integration test stub - implement when needed")
    async def test_complete_order_workflow(self):
        """Test complete order workflow: create -> update -> cancel."""
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Integration test stub - implement when needed")
    async def test_order_workflow_with_entity_service(self):
        """Test order workflow with actual EntityService integration."""
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Integration test stub - implement when needed")
    async def test_order_workflow_with_external_service(self):
        """Test order workflow with actual external service calls."""
        pass
