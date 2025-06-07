# ABOUTME: Test suite for workflow processing functions in routes/routes.py
# ABOUTME: Tests the business logic for processing subscribe and fetch requests

import pytest
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from routes.routes import (
    process_subscribe_request,
    process_fetch_request,
    fetch_nba_scores
)
from entity.subscriber_notification_message.workflow import (
    process_send_notification,
    process_retry_notification,
    process_cancel_notification
)


class TestProcessSubscribeRequest:
    """Test cases for process_subscribe_request workflow function."""

    @pytest.mark.asyncio
    async def test_process_subscribe_request_success(self):
        """Test successful processing of subscribe request."""
        entity = {
            "email": "test@example.com",
            "notificationtype": "summary"
        }
        
        result = await process_subscribe_request(entity)
        
        assert result["email"] == "test@example.com"
        assert result["notificationtype"] == "summary"
        assert "processed_at" in result
        # Verify the timestamp is recent (within last minute)
        processed_time = datetime.datetime.fromisoformat(result["processed_at"])
        now = datetime.datetime.utcnow()
        assert (now - processed_time).total_seconds() < 60

    @pytest.mark.asyncio
    async def test_process_subscribe_request_preserves_data(self):
        """Test that processing preserves original entity data."""
        entity = {
            "email": "test@example.com",
            "notificationtype": "full",
            "extra_field": "extra_value"
        }
        
        result = await process_subscribe_request(entity)
        
        assert result["email"] == "test@example.com"
        assert result["notificationtype"] == "full"
        assert result["extra_field"] == "extra_value"
        assert "processed_at" in result


class TestProcessFetchRequest:
    """Test cases for process_fetch_request workflow function."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for fetch request processing."""
        with patch('routes.routes.fetch_nba_scores') as mock_fetch, \
             patch('routes.routes.entity_service') as mock_entity_service, \
             patch('routes.routes.cyoda_auth_service') as mock_auth_service:
            
            mock_fetch.return_value = [
                {"Day": "2024-01-01", "AwayTeam": "LAL", "HomeTeam": "GSW", 
                 "AwayTeamScore": 110, "HomeTeamScore": 105}
            ]
            mock_entity_service.add_item = AsyncMock()
            mock_entity_service.get_items = AsyncMock(return_value=[])
            mock_auth_service.get_bearer_token = AsyncMock(return_value="mock_token")
            
            yield mock_fetch, mock_entity_service, mock_auth_service

    @pytest.mark.asyncio
    async def test_process_fetch_request_single_date(self, mock_dependencies):
        """Test processing fetch request for a single date."""
        mock_fetch, mock_entity_service, mock_auth_service = mock_dependencies
        
        entity = {
            "api_key": "test_key",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01"
        }
        
        result = await process_fetch_request(entity)
        
        assert result["processed_at"] is not None
        assert result["status"] == "completed"
        
        # Verify NBA scores were fetched
        mock_fetch.assert_called_once_with("2024-01-01", "test_key")
        
        # Verify games were saved
        mock_entity_service.add_item.assert_called_once()
        call_args = mock_entity_service.add_item.call_args
        assert call_args[1]['entity_model'] == "game"
        assert call_args[1]['entity']['date'] == "2024-01-01"

    @pytest.mark.asyncio
    async def test_process_fetch_request_date_range(self, mock_dependencies):
        """Test processing fetch request for a date range."""
        mock_fetch, mock_entity_service, mock_auth_service = mock_dependencies
        
        entity = {
            "api_key": "test_key",
            "start_date": "2024-01-01",
            "end_date": "2024-01-03"
        }
        
        result = await process_fetch_request(entity)
        
        assert result["status"] == "completed"
        
        # Verify NBA scores were fetched for each date
        assert mock_fetch.call_count == 3
        expected_dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        actual_dates = [call[0][0] for call in mock_fetch.call_args_list]
        assert actual_dates == expected_dates

    @pytest.mark.asyncio
    async def test_process_fetch_request_no_dates(self, mock_dependencies):
        """Test processing fetch request with no dates (defaults to current date)."""
        mock_fetch, mock_entity_service, mock_auth_service = mock_dependencies
        
        entity = {"api_key": "test_key"}
        
        with patch('routes.routes.datetime') as mock_datetime:
            mock_now = datetime.datetime(2024, 1, 15, 12, 0, 0)
            mock_datetime.datetime.utcnow.return_value = mock_now
            mock_datetime.datetime.strptime = datetime.datetime.strptime
            mock_datetime.timedelta = datetime.timedelta
            
            result = await process_fetch_request(entity)
        
        assert result["status"] == "completed"
        mock_fetch.assert_called_once_with("2024-01-15", "test_key")

    @pytest.mark.asyncio
    async def test_process_fetch_request_swaps_dates(self, mock_dependencies):
        """Test that start_date and end_date are swapped if start > end."""
        mock_fetch, mock_entity_service, mock_auth_service = mock_dependencies
        
        entity = {
            "api_key": "test_key",
            "start_date": "2024-01-03",  # Later date
            "end_date": "2024-01-01"     # Earlier date
        }
        
        result = await process_fetch_request(entity)
        
        assert result["status"] == "completed"
        
        # Verify dates were processed in correct order
        expected_dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        actual_dates = [call[0][0] for call in mock_fetch.call_args_list]
        assert actual_dates == expected_dates

    @pytest.mark.asyncio
    async def test_process_fetch_request_invalid_date_format(self, mock_dependencies):
        """Test processing with invalid date format."""
        mock_fetch, mock_entity_service, mock_auth_service = mock_dependencies
        
        entity = {
            "api_key": "test_key",
            "start_date": "invalid-date"
        }
        
        result = await process_fetch_request(entity)
        
        # Should return original entity without processing
        assert result == entity
        mock_fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_fetch_request_fetch_failure(self, mock_dependencies):
        """Test processing when NBA scores fetch fails."""
        mock_fetch, mock_entity_service, mock_auth_service = mock_dependencies
        mock_fetch.return_value = None  # Simulate fetch failure
        
        entity = {
            "api_key": "test_key",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01"
        }
        
        result = await process_fetch_request(entity)
        
        assert result["status"] == "completed"
        # Should not try to save games when fetch fails
        mock_entity_service.add_item.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_fetch_request_with_subscribers(self, mock_dependencies):
        """Test processing with email notifications to subscribers."""
        mock_fetch, mock_entity_service, mock_auth_service = mock_dependencies
        
        # Mock subscribers
        subscribers = [
            {"email": "user1@example.com", "notificationtype": "summary"},
            {"email": "user2@example.com", "notificationtype": "full"}
        ]
        mock_entity_service.get_items.return_value = subscribers
        
        entity = {
            "api_key": "test_key",
            "start_date": "2024-01-01",
            "end_date": "2024-01-01"
        }
        
        with patch('routes.routes.send_email') as mock_send_email:
            result = await process_fetch_request(entity)
        
        assert result["status"] == "completed"
        
        # Verify emails were sent to both subscribers
        assert mock_send_email.call_count == 2
        
        # Check email calls
        email_calls = mock_send_email.call_args_list
        assert "user1@example.com" in email_calls[0][0]
        assert "user2@example.com" in email_calls[1][0]


class TestFetchNbaScores:
    """Test cases for fetch_nba_scores function."""

    @pytest.mark.asyncio
    async def test_fetch_nba_scores_success(self):
        """Test successful NBA scores fetch."""
        mock_response_data = [
            {"GameID": 1, "AwayTeam": "LAL", "HomeTeam": "GSW"}
        ]
        
        with patch('routes.routes.cyoda_auth_service') as mock_auth, \
             patch('httpx.AsyncClient') as mock_client_class:
            
            mock_auth.get_bearer_token.return_value = "mock_token"
            
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await fetch_nba_scores("2024-01-01", "test_api_key")
        
        assert result == mock_response_data
        mock_client.get.assert_called_once()
        
        # Verify URL construction
        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert "2024-01-01" in url
        assert "test_api_key" in url

    @pytest.mark.asyncio
    async def test_fetch_nba_scores_http_error(self):
        """Test NBA scores fetch with HTTP error."""
        with patch('routes.routes.cyoda_auth_service') as mock_auth, \
             patch('httpx.AsyncClient') as mock_client_class:
            
            mock_auth.get_bearer_token.return_value = "mock_token"
            
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.text = "Not Found"
            
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.get.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=None, response=mock_response
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await fetch_nba_scores("2024-01-01", "test_api_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_nba_scores_general_exception(self):
        """Test NBA scores fetch with general exception."""
        with patch('routes.routes.cyoda_auth_service') as mock_auth, \
             patch('httpx.AsyncClient') as mock_client_class:
            
            mock_auth.get_bearer_token.return_value = "mock_token"
            
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Network error")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            result = await fetch_nba_scores("2024-01-01", "test_api_key")
        
        assert result is None


class TestSubscriberNotificationMessage:
    """Test cases for subscriber_notification_message workflow functions."""

    @pytest.mark.asyncio
    async def test_process_send_notification_summary_success(self):
        """Test successful sending of summary notification."""
        entity = {
            "subscriber_email": "test@example.com",
            "notification_type": "summary",
            "date": "2024-01-01",
            "scores_data": [
                {"Day": "2024-01-01", "AwayTeam": "LAL", "HomeTeam": "GSW",
                 "AwayTeamScore": 110, "HomeTeamScore": 105}
            ]
        }

        with patch('entity.subscriber_notification_message.workflow.send_email') as mock_send_email:
            result = await process_send_notification(entity)

        assert result["status"] == "sent"
        assert "sent_at" in result
        assert result["retry_count"] == 0

        # Verify email was sent
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert call_args[0][0] == "test@example.com"
        assert "NBA Scores Summary for 2024-01-01" in call_args[0][1]
        assert call_args[1]["html"] is False

    @pytest.mark.asyncio
    async def test_process_send_notification_full_success(self):
        """Test successful sending of full notification."""
        entity = {
            "subscriber_email": "test@example.com",
            "notification_type": "full",
            "date": "2024-01-01",
            "scores_data": [
                {"Day": "2024-01-01", "AwayTeam": "LAL", "HomeTeam": "GSW",
                 "AwayTeamScore": 110, "HomeTeamScore": 105}
            ]
        }

        with patch('entity.subscriber_notification_message.workflow.send_email') as mock_send_email:
            result = await process_send_notification(entity)

        assert result["status"] == "sent"
        assert "sent_at" in result

        # Verify HTML email was sent
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert call_args[0][0] == "test@example.com"
        assert "NBA Scores Full Listing for 2024-01-01" in call_args[0][1]
        assert call_args[1]["html"] is True

    @pytest.mark.asyncio
    async def test_process_send_notification_missing_fields(self):
        """Test sending notification with missing required fields."""
        entity = {
            "subscriber_email": "test@example.com",
            # Missing notification_type and date
            "scores_data": []
        }

        result = await process_send_notification(entity)

        assert result["status"] == "failed"
        assert "Missing required fields" in result["error_message"]

    @pytest.mark.asyncio
    async def test_process_send_notification_email_failure(self):
        """Test handling of email sending failure."""
        entity = {
            "subscriber_email": "test@example.com",
            "notification_type": "summary",
            "date": "2024-01-01",
            "scores_data": []
        }

        with patch('entity.subscriber_notification_message.workflow.send_email') as mock_send_email:
            mock_send_email.side_effect = Exception("SMTP error")
            result = await process_send_notification(entity)

        assert result["status"] == "failed"
        assert "SMTP error" in result["error_message"]
        assert "last_attempt_at" in result

    @pytest.mark.asyncio
    async def test_process_retry_notification_success(self):
        """Test successful retry of failed notification."""
        entity = {
            "subscriber_email": "test@example.com",
            "notification_type": "summary",
            "date": "2024-01-01",
            "scores_data": [],
            "retry_count": 1,
            "max_retries": 3
        }

        with patch('entity.subscriber_notification_message.workflow.send_email') as mock_send_email:
            result = await process_retry_notification(entity)

        assert result["status"] == "sent"
        assert result["retry_count"] == 2  # Incremented

    @pytest.mark.asyncio
    async def test_process_retry_notification_max_retries_exceeded(self):
        """Test retry when max retries exceeded."""
        entity = {
            "subscriber_email": "test@example.com",
            "notification_type": "summary",
            "date": "2024-01-01",
            "scores_data": [],
            "retry_count": 3,
            "max_retries": 3
        }

        result = await process_retry_notification(entity)

        assert result["status"] == "failed_max_retries"
        assert "Maximum retry attempts (3) exceeded" in result["error_message"]

    @pytest.mark.asyncio
    async def test_process_cancel_notification(self):
        """Test cancelling a notification."""
        entity = {
            "subscriber_email": "test@example.com",
            "notification_type": "summary",
            "date": "2024-01-01",
            "scores_data": []
        }

        result = await process_cancel_notification(entity)

        assert result["status"] == "cancelled"
        assert "cancelled_at" in result
