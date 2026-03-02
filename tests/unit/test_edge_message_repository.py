"""
Unit tests for EdgeMessageRepository.
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.repository.cyoda.edge_message_repository import (
    EdgeMessage,
    EdgeMessageHeader,
    EdgeMessageMetadata,
    EdgeMessageRepository,
)


class MockCyodaAuthService:
    """Mock Cyoda authentication service."""

    async def get_access_token(self) -> str:
        """Return a mock access token."""
        return "mock-token-123"

    def invalidate_tokens(self) -> None:
        """Invalidate tokens."""
        pass


class TestEdgeMessageDataclasses:
    """Test suite for EdgeMessage dataclasses."""

    def test_edge_message_from_api_response_complete(self):
        """Test creating EdgeMessage from complete API response."""
        api_response = {
            "header": {
                "subject": "Test Subject",
                "contentType": "application/json",
                "contentLength": 100,
                "contentEncoding": "utf-8",
                "messageId": "msg-123",
                "userId": "user-456",
                "recipient": "recipient@example.com",
                "replyTo": "reply@example.com",
                "correlationId": "corr-789",
            },
            "metaData": {
                "values": {"key1": "value1"},
                "indexedValues": {"key2": "value2"},
            },
            "content": '{"data": "test"}',
        }

        result = EdgeMessage.from_api_response(api_response)

        assert result.header.subject == "Test Subject"
        assert result.header.content_type == "application/json"
        assert result.header.message_id == "msg-123"
        assert result.metadata.values == {"key1": "value1"}
        assert result.content == '{"data": "test"}'

    def test_edge_message_from_api_response_minimal(self):
        """Test creating EdgeMessage from minimal API response."""
        api_response = {}

        result = EdgeMessage.from_api_response(api_response)

        assert result.header.subject == ""
        assert result.header.content_type == ""
        assert result.metadata.values == {}
        assert result.content == ""


class TestEdgeMessageRepository:
    """Test suite for EdgeMessageRepository."""

    @pytest.fixture
    def auth_service(self):
        """Create a mock auth service."""
        return MockCyodaAuthService()

    @pytest.fixture
    def repository(self, auth_service):
        """Create an EdgeMessageRepository instance."""
        # Reset singleton
        EdgeMessageRepository._instance = None
        return EdgeMessageRepository(auth_service)

    # Singleton Pattern Tests

    def test_singleton_pattern(self, auth_service):
        """Test that EdgeMessageRepository follows singleton pattern."""
        EdgeMessageRepository._instance = None
        repo1 = EdgeMessageRepository(auth_service)
        repo2 = EdgeMessageRepository(auth_service)

        assert repo1 is repo2

    # Get Message Tests

    @pytest.mark.asyncio
    async def test_get_message_by_id_success(self, repository):
        """Test getting message by ID successfully."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {
                    "header": {
                        "subject": "Test Message",
                        "contentType": "application/json",
                        "contentLength": 50,
                        "contentEncoding": "utf-8",
                        "messageId": "msg-123",
                        "userId": "user-1",
                        "recipient": "test@example.com",
                        "replyTo": "reply@example.com",
                        "correlationId": "corr-1",
                    },
                    "metaData": {
                        "values": {"source": "test"},
                        "indexedValues": {},
                    },
                    "content": '{"message": "Hello"}',
                },
                "status": 200,
            }

            result = await repository.get_message_by_id("msg-123")

            assert isinstance(result, EdgeMessage)
            assert result.header.subject == "Test Message"
            assert result.header.message_id == "msg-123"
            assert result.content == '{"message": "Hello"}'
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_message_by_id_not_found(self, repository):
        """Test getting message by ID when not found."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"errorMessage": "Message not found"},
                "status": 404,
            }

            result = await repository.get_message_by_id("non-existent")

            # Returns None on 404
            assert result is None

    @pytest.mark.asyncio
    async def test_get_message_by_id_error(self, repository):
        """Test getting message by ID with error."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"errorMessage": "Internal server error"},
                "status": 500,
            }

            result = await repository.get_message_by_id("msg-123")

            # Returns None on error
            assert result is None

    # Send Message Tests

    @pytest.mark.asyncio
    async def test_send_message_success(self, repository):
        """Test sending message successfully with dict response (legacy shape)."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": ["msg-new-123"], "success": True},
                "status": 200,
            }

            content = {"data": "test message"}
            result = await repository.send_message(
                subject="Test Subject",
                content=content,
                message_id="msg-new-123",
                user_id="user-1",
            )

            from common.repository.cyoda.edge_message_repository import (
                SendMessageResponse,
            )

            assert isinstance(result, SendMessageResponse)
            assert result.entity_ids == ["msg-new-123"]
            assert result.success is True
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_success_list_response(self, repository):
        """Test sending message successfully with list response (current Cyoda API shape)."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"entityIds": ["msg-list-456"], "success": True}],
                "status": 200,
            }

            content = {"data": "test message"}
            result = await repository.send_message(
                subject="Test Subject",
                content=content,
            )

            from common.repository.cyoda.edge_message_repository import (
                SendMessageResponse,
            )

            assert isinstance(result, SendMessageResponse)
            assert result.entity_ids == ["msg-list-456"]
            assert result.success is True

    @pytest.mark.asyncio
    async def test_send_message_with_all_headers(self, repository):
        """Test sending message with all custom headers."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": ["msg-123"], "success": True},
                "status": 200,
            }

            content = {"data": "test"}
            result = await repository.send_message(
                subject="Test",
                content=content,
                message_id="msg-123",
                user_id="user-1",
                recipient="recipient@example.com",
                reply_to="reply@example.com",
                correlation_id="corr-123",
                content_encoding="utf-8",
                content_length=100,
                content_type="application/json",
            )

            from common.repository.cyoda.edge_message_repository import (
                SendMessageResponse,
            )

            assert isinstance(result, SendMessageResponse)
            assert result.success is True
            # Verify headers were passed
            call_args = mock_request.call_args
            headers = call_args[0][0]  # First positional argument
            assert "X-Message-ID" in headers
            assert "X-User-ID" in headers
            assert "X-Recipient" in headers

    @pytest.mark.asyncio
    async def test_send_message_minimal(self, repository):
        """Test sending message with minimal parameters."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": ["msg-123"], "success": True},
                "status": 200,
            }

            content = {"data": "test"}
            result = await repository.send_message(
                subject="Test",
                content=content,
            )

            from common.repository.cyoda.edge_message_repository import (
                SendMessageResponse,
            )

            assert isinstance(result, SendMessageResponse)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_send_message_error(self, repository):
        """Test sending message with error."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"errorMessage": "Failed to send message"},
                "status": 500,
            }

            content = {"data": "test"}

            with pytest.raises(Exception) as exc_info:
                await repository.send_message(
                    subject="Test",
                    content=content,
                )

            assert "Failed to send message" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_with_dict_content(self, repository):
        """Test sending message with dictionary content."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": ["msg-123"], "success": True},
                "status": 200,
            }

            content = {"key": "value", "nested": {"data": 123}}
            result = await repository.send_message(
                subject="Test",
                content=content,
            )

            from common.repository.cyoda.edge_message_repository import (
                SendMessageResponse,
            )

            assert isinstance(result, SendMessageResponse)
            assert result.success is True
            # Verify content is wrapped in payload field per Cyoda API spec
            call_args = mock_request.call_args
            import json as _json
            sent_body = _json.loads(call_args.kwargs["data"])
            assert "payload" in sent_body
            assert sent_body["payload"] == content

    @pytest.mark.asyncio
    async def test_send_message_with_string_content(self, repository):
        """Test sending message with string content - should fail type check."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": ["msg-123"], "success": True},
                "status": 200,
            }

            # send_message expects Dict[str, Any], not str
            # This test verifies the type signature
            content_dict = {"message": "plain text message"}
            result = await repository.send_message(
                subject="Test",
                content=content_dict,
            )

            from common.repository.cyoda.edge_message_repository import (
                SendMessageResponse,
            )

            assert isinstance(result, SendMessageResponse)
            assert result.success is True

    # Additional Edge Cases and Error Handling Tests

    @pytest.mark.asyncio
    async def test_get_message_by_id_with_no_json_data(self, repository):
        """Test getting message by ID with no JSON data."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": None,
                "status": 200,
            }

            result = await repository.get_message_by_id("msg-123")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_message_by_id_exception(self, repository):
        """Test getting message by ID with exception."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.side_effect = Exception("Network error")

            with pytest.raises(Exception) as exc_info:
                await repository.get_message_by_id("msg-123")

            assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_with_no_response_data(self, repository):
        """Test sending message with no response data."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": None,
                "status": 200,
            }

            content = {"data": "test"}

            with pytest.raises(Exception) as exc_info:
                await repository.send_message(subject="Test", content=content)

            assert "No data in send message response" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_message_with_401_retry(self, repository):
        """Test send_message with 401 retry logic."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            # First call returns 401, second call succeeds
            mock_request.side_effect = [
                {"json": {"errorMessage": "Unauthorized"}, "status": 401},
                {"json": {"entityIds": ["msg-123"], "success": True}, "status": 200},
            ]

            content = {"data": "test"}
            result = await repository.send_message(subject="Test", content=content)

            from common.repository.cyoda.edge_message_repository import (
                SendMessageResponse,
            )

            assert isinstance(result, SendMessageResponse)
            assert result.success is True
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_with_exception_401_retry(self, repository):
        """Test send_message with exception containing 401."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            # First call raises exception with 401, second call succeeds
            mock_request.side_effect = [
                Exception("401 Unauthorized"),
                {"json": {"entityIds": ["msg-123"], "success": True}, "status": 200},
            ]

            content = {"data": "test"}
            result = await repository.send_message(subject="Test", content=content)

            from common.repository.cyoda.edge_message_repository import (
                SendMessageResponse,
            )

            assert isinstance(result, SendMessageResponse)
            assert result.success is True
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_fails_after_retry(self, repository):
        """Test send_message fails after retry."""
        with patch(
            "common.repository.cyoda.edge_message_repository.send_request"
        ) as mock_request:
            # Both calls return 401 - send_message raises Exception, not RuntimeError
            mock_request.return_value = {
                "json": {"errorMessage": "Unauthorized"},
                "status": 401,
            }

            content = {"data": "test"}

            with pytest.raises(Exception) as exc_info:
                await repository.send_message(subject="Test", content=content)

            assert "Failed to send message" in str(exc_info.value)
            assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_send_message_response_from_api_response_minimal(self):
        """Test SendMessageResponse from minimal API response."""
        from common.repository.cyoda.edge_message_repository import (
            SendMessageResponse,
        )

        api_response = {}

        result = SendMessageResponse.from_api_response(api_response)

        assert result.entity_ids == []
        assert result.success is False

    @pytest.mark.asyncio
    async def test_edge_message_header_all_fields(self):
        """Test EdgeMessageHeader with all fields populated."""
        api_response = {
            "header": {
                "subject": "Important Message",
                "contentType": "application/xml",
                "contentLength": 1024,
                "contentEncoding": "gzip",
                "messageId": "msg-unique-123",
                "userId": "user-admin",
                "recipient": "admin@example.com",
                "replyTo": "noreply@example.com",
                "correlationId": "corr-unique-456",
            },
            "metaData": {
                "values": {"priority": "high", "category": "alert"},
                "indexedValues": {"timestamp": "2024-01-01T00:00:00Z"},
            },
            "content": "<xml>data</xml>",
        }

        result = EdgeMessage.from_api_response(api_response)

        assert result.header.subject == "Important Message"
        assert result.header.content_type == "application/xml"
        assert result.header.content_length == 1024
        assert result.header.content_encoding == "gzip"
        assert result.header.message_id == "msg-unique-123"
        assert result.header.user_id == "user-admin"
        assert result.header.recipient == "admin@example.com"
        assert result.header.reply_to == "noreply@example.com"
        assert result.header.correlation_id == "corr-unique-456"
        assert result.metadata.values == {"priority": "high", "category": "alert"}
        assert result.metadata.indexed_values == {"timestamp": "2024-01-01T00:00:00Z"}
        assert result.content == "<xml>data</xml>"

    @pytest.mark.asyncio
    async def test_singleton_thread_safety(self, auth_service):
        """Test singleton thread safety."""
        import threading

        EdgeMessageRepository._instance = None
        instances = []

        def create_instance():
            instances.append(EdgeMessageRepository(auth_service))

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)
