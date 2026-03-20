"""
Unit tests for GrpcStreamingFacade.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import grpc
import pytest

from common.grpc_client.facade import GrpcStreamingFacade
from common.grpc_client.middleware.base import MiddlewareLink
from common.grpc_client.outbox import Outbox
from common.grpc_client.responses.builders import ResponseBuilderRegistry
from common.grpc_client.router import EventRouter
from common.proto.cloudevents_pb2 import CloudEvent


class TestGrpcStreamingFacade:
    """Test suite for GrpcStreamingFacade."""

    @pytest.fixture
    def mock_auth(self):
        """Create mock auth object."""
        auth = Mock()
        auth.get_access_token_sync.return_value = "test-token-123"
        auth.invalidate_tokens = Mock()
        return auth

    @pytest.fixture
    def router(self):
        """Create EventRouter instance."""
        return EventRouter()

    @pytest.fixture
    def builders(self):
        """Create ResponseBuilderRegistry instance."""
        return ResponseBuilderRegistry()

    @pytest.fixture
    def outbox(self):
        """Create Outbox instance."""
        return Outbox()

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        middleware = MiddlewareLink()
        middleware.handle = AsyncMock(return_value=None)
        return middleware

    @pytest.fixture
    def facade(self, mock_auth, router, builders, outbox, middleware):
        """Create GrpcStreamingFacade instance."""
        return GrpcStreamingFacade(
            auth=mock_auth,
            router=router,
            builders=builders,
            outbox=outbox,
            first_middleware=middleware,
        )

    def test_facade_initialization(
        self, facade, mock_auth, router, builders, outbox, middleware
    ):
        """Test facade initialization."""
        assert facade.auth is mock_auth
        assert facade.router is router
        assert facade.builders is builders
        assert facade.outbox is outbox
        assert facade.first_middleware is middleware
        assert facade._running is False
        assert facade.grpc_client is None

    def test_facade_initialization_with_grpc_client(
        self, mock_auth, router, builders, outbox, middleware
    ):
        """Test facade initialization with grpc_client."""
        mock_grpc_client = Mock()
        facade = GrpcStreamingFacade(
            auth=mock_auth,
            router=router,
            builders=builders,
            outbox=outbox,
            first_middleware=middleware,
            grpc_client=mock_grpc_client,
        )

        assert facade.grpc_client is mock_grpc_client

    def test_metadata_callback_success(self, facade, mock_auth):
        """Test metadata callback with successful token fetch."""
        context = Mock()
        callback = Mock()

        facade.metadata_callback(context, callback)

        mock_auth.get_access_token_sync.assert_called_once()
        callback.assert_called_once_with(
            [("authorization", "Bearer test-token-123")], None
        )

    def test_metadata_callback_retry_on_failure(self, facade, mock_auth):
        """Test metadata callback retries on token fetch failure."""
        context = Mock()
        callback = Mock()

        # First call fails, second succeeds
        mock_auth.get_access_token_sync.side_effect = [
            Exception("Token fetch failed"),
            "retry-token-456",
        ]

        facade.metadata_callback(context, callback)

        # Should have called twice (initial + retry)
        assert mock_auth.get_access_token_sync.call_count == 2
        # Should have invalidated tokens
        mock_auth.invalidate_tokens.assert_called_once()
        # Should have called callback with retry token
        callback.assert_called_once_with(
            [("authorization", "Bearer retry-token-456")], None
        )

    @patch("common.grpc_client.facade.grpc")
    def test_get_grpc_credentials(self, mock_grpc_module, facade):
        """Test getting gRPC credentials."""
        mock_call_creds = Mock()
        mock_ssl_creds = Mock()
        mock_composite_creds = Mock()

        mock_grpc_module.metadata_call_credentials.return_value = mock_call_creds
        mock_grpc_module.ssl_channel_credentials.return_value = mock_ssl_creds
        mock_grpc_module.composite_channel_credentials.return_value = (
            mock_composite_creds
        )

        result = facade.get_grpc_credentials()

        mock_grpc_module.metadata_call_credentials.assert_called_once()
        mock_grpc_module.ssl_channel_credentials.assert_called_once()
        mock_grpc_module.composite_channel_credentials.assert_called_once_with(
            mock_ssl_creds, mock_call_creds
        )
        assert result is mock_composite_creds

    @pytest.mark.asyncio
    async def test_on_event(self, facade, middleware):
        """Test _on_event dispatches event through middleware via an asyncio task."""
        event = CloudEvent()
        event.id = "test-123"
        event.type = "TestEvent"

        facade._on_event(event)
        await asyncio.sleep(0)  # yield to the event loop so the task runs

        middleware.handle.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_stop(self, facade):
        """Test stopping the facade sets _running to False and closes the outbox."""
        facade._running = True

        facade.stop()
        await asyncio.sleep(0)  # yield so the outbox.close() task completes

        assert facade._running is False

    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self, facade):
        """Test that start sets _running flag."""
        # Mock _consume_stream to avoid actual streaming
        facade._consume_stream = AsyncMock()

        await facade.start()

        assert facade._running is True
        facade._consume_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_consume_stream_stops_when_not_running(self, facade):
        """Test that consume stream stops when _running is False."""
        facade._running = False

        # Mock get_grpc_credentials to avoid actual credential creation
        facade.get_grpc_credentials = Mock()

        # Should exit immediately without creating channel
        await facade._consume_stream()

        facade.get_grpc_credentials.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_stream_handles_rpc_error(self, facade, mock_auth):
        """Test that consume stream handles RPC errors."""
        facade._running = True

        # Create mock RPC error
        rpc_error = grpc.RpcError()
        rpc_error.code = Mock(return_value=grpc.StatusCode.UNAVAILABLE)
        rpc_error.details = Mock(return_value="Service unavailable")
        rpc_error.debug_error_string = Mock(return_value="Debug info")

        # Mock get_grpc_credentials
        mock_creds = Mock()
        facade.get_grpc_credentials = Mock(return_value=mock_creds)

        with patch("common.grpc_client.facade.grpc.aio.secure_channel") as mock_channel:
            # Make the channel raise RPC error
            mock_channel.return_value.__aenter__.side_effect = rpc_error

            # Stop after first iteration
            def stop_after_sleep(delay):
                facade._running = False

            with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_sleep):
                await facade._consume_stream()

        # Should have attempted to get credentials
        assert facade.get_grpc_credentials.call_count > 0

    @pytest.mark.asyncio
    async def test_consume_stream_handles_unauthenticated_error(
        self, facade, mock_auth
    ):
        """Test that consume stream handles UNAUTHENTICATED errors."""
        facade._running = True

        # Create mock UNAUTHENTICATED error
        rpc_error = grpc.RpcError()
        rpc_error.code = Mock(return_value=grpc.StatusCode.UNAUTHENTICATED)
        rpc_error.details = Mock(return_value="Unauthenticated")
        rpc_error.debug_error_string = Mock(return_value="Auth failed")

        with patch("common.grpc_client.facade.grpc.aio.secure_channel") as mock_channel:
            # Make the channel raise UNAUTHENTICATED error
            mock_channel.return_value.__aenter__.side_effect = rpc_error

            # Stop after first iteration
            def stop_after_sleep(delay):
                facade._running = False

            with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_sleep):
                await facade._consume_stream()

        # Should have invalidated tokens
        mock_auth.invalidate_tokens.assert_called()

    @pytest.mark.asyncio
    async def test_consume_stream_handles_generic_exception(self, facade):
        """Test that consume stream handles generic exceptions."""
        facade._running = True

        # Mock get_grpc_credentials
        mock_creds = Mock()
        facade.get_grpc_credentials = Mock(return_value=mock_creds)

        with patch("common.grpc_client.facade.grpc.aio.secure_channel") as mock_channel:
            # Make the channel raise generic exception
            mock_channel.return_value.__aenter__.side_effect = Exception(
                "Unexpected error"
            )

            # Stop after first iteration
            def stop_after_sleep(delay):
                facade._running = False

            with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_sleep):
                await facade._consume_stream()

        # Should have attempted to get credentials
        assert facade.get_grpc_credentials.call_count > 0

    @pytest.mark.asyncio
    async def test_consume_stream_backoff_increases(self, facade):
        """Test that consume stream backoff increases on errors."""
        facade._running = True
        sleep_delays = []

        with patch("common.grpc_client.facade.grpc.aio.secure_channel") as mock_channel:
            # Make the channel raise exception multiple times
            mock_channel.return_value.__aenter__.side_effect = Exception("Error")

            # Track sleep delays and stop after 3 iterations
            def track_sleep(delay):
                sleep_delays.append(delay)
                if len(sleep_delays) >= 3:
                    facade._running = False

            with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=track_sleep):
                await facade._consume_stream()

        # Verify backoff increases: 1, 2, 4
        assert len(sleep_delays) >= 3
        assert sleep_delays[0] == 1
        assert sleep_delays[1] == 2
        assert sleep_delays[2] == 4

    @pytest.mark.asyncio
    async def test_consume_stream_backoff_max_30(self, facade):
        """Test that consume stream backoff maxes out at 30 seconds."""
        facade._running = True
        sleep_delays = []

        with patch("common.grpc_client.facade.grpc.aio.secure_channel") as mock_channel:
            # Make the channel raise exception many times
            mock_channel.return_value.__aenter__.side_effect = Exception("Error")

            # Track sleep delays and stop after 10 iterations
            def track_sleep(delay):
                sleep_delays.append(delay)
                if len(sleep_delays) >= 10:
                    facade._running = False

            with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=track_sleep):
                await facade._consume_stream()

        # Verify backoff maxes at 30: 1, 2, 4, 8, 16, 30, 30, 30, 30, 30
        assert max(sleep_delays) == 30
        # After reaching 30, should stay at 30
        assert all(delay == 30 for delay in sleep_delays[-3:])
