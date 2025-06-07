# ABOUTME: Comprehensive test suite for all API endpoints in routes/routes.py
# ABOUTME: Tests subscription management, game data retrieval, and external API integration

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from quart import Quart
import httpx

from routes.routes import routes_bp


class TestSubscribeEndpoint:
    """Test cases for POST /subscribe endpoint."""

    @pytest.mark.asyncio
    async def test_subscribe_success(self, test_client, mock_services, sample_subscriber_data):
        """Test successful subscription creation."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.add_item.return_value = "test_id_123"

        response = await test_client.post('/subscribe', json=sample_subscriber_data)
        
        assert response.status_code == 200
        data = await response.get_json()
        assert data == {"id": "test_id_123"}
        
        # Verify service was called with correct parameters
        mock_entity_service.add_item.assert_called_once()
        call_args = mock_entity_service.add_item.call_args
        assert call_args[1]['entity_model'] == "subscribe_request"
        assert call_args[1]['entity']['email'] == "test@example.com"
        assert call_args[1]['entity']['notificationtype'] == "summary"

    @pytest.mark.asyncio
    async def test_subscribe_invalid_notification_type(self, test_client):
        """Test subscription with invalid notification type."""
        invalid_data = {
            "email": "test@example.com",
            "notificationType": "invalid_type"
        }
        
        response = await test_client.post('/subscribe', json=invalid_data)
        
        assert response.status_code == 400
        data = await response.get_json()
        assert "Invalid notificationType" in data["error"]

    @pytest.mark.asyncio
    async def test_subscribe_missing_fields(self, test_client):
        """Test subscription with missing required fields."""
        incomplete_data = {"email": "test@example.com"}
        
        response = await test_client.post('/subscribe', json=incomplete_data)
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_subscribe_service_error(self, test_client, mock_services, sample_subscriber_data):
        """Test subscription when service throws an error."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.add_item.side_effect = Exception("Service error")

        response = await test_client.post('/subscribe', json=sample_subscriber_data)
        
        assert response.status_code == 500
        data = await response.get_json()
        assert "Failed to add subscription" in data["error"]


class TestUnsubscribeEndpoint:
    """Test cases for DELETE /subscribe endpoint."""

    @pytest.mark.asyncio
    async def test_unsubscribe_success(self, test_client, mock_services, sample_subscribers_list):
        """Test successful unsubscription."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.return_value = sample_subscribers_list
        mock_entity_service.delete_item.return_value = None

        unsubscribe_data = {"email": "user1@example.com"}
        response = await test_client.delete('/subscribe', json=unsubscribe_data)
        
        assert response.status_code == 200
        data = await response.get_json()
        assert "Subscription removed successfully" in data["message"]
        
        # Verify delete was called with correct ID
        mock_entity_service.delete_item.assert_called_once()
        call_args = mock_entity_service.delete_item.call_args
        assert call_args[1]['technical_id'] == "1"

    @pytest.mark.asyncio
    async def test_unsubscribe_email_not_found(self, test_client, mock_services, sample_subscribers_list):
        """Test unsubscription with non-existent email."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.return_value = sample_subscribers_list

        unsubscribe_data = {"email": "nonexistent@example.com"}
        response = await test_client.delete('/subscribe', json=unsubscribe_data)
        
        assert response.status_code == 404
        data = await response.get_json()
        assert "Email not found" in data["error"]

    @pytest.mark.asyncio
    async def test_unsubscribe_get_subscribers_error(self, test_client, mock_services):
        """Test unsubscription when getting subscribers fails."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.side_effect = Exception("Database error")

        unsubscribe_data = {"email": "test@example.com"}
        response = await test_client.delete('/subscribe', json=unsubscribe_data)
        
        assert response.status_code == 500
        data = await response.get_json()
        assert "Failed to get subscribers" in data["error"]

    @pytest.mark.asyncio
    async def test_unsubscribe_delete_error(self, test_client, mock_services, sample_subscribers_list):
        """Test unsubscription when delete operation fails."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.return_value = sample_subscribers_list
        mock_entity_service.delete_item.side_effect = Exception("Delete error")

        unsubscribe_data = {"email": "user1@example.com"}
        response = await test_client.delete('/subscribe', json=unsubscribe_data)
        
        assert response.status_code == 500
        data = await response.get_json()
        assert "Failed to remove subscription" in data["error"]


class TestGetSubscribersEndpoint:
    """Test cases for GET /subscribers endpoint."""

    @pytest.mark.asyncio
    async def test_get_subscribers_success(self, test_client, mock_services, sample_subscribers_list):
        """Test successful retrieval of subscribers."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.return_value = sample_subscribers_list

        response = await test_client.get('/subscribers')
        
        assert response.status_code == 200
        data = await response.get_json()
        assert len(data) == 2
        assert data[0]["email"] == "user1@example.com"
        assert data[0]["notificationType"] == "summary"
        assert data[1]["email"] == "user2@example.com"
        assert data[1]["notificationType"] == "full"

    @pytest.mark.asyncio
    async def test_get_subscribers_empty_list(self, test_client, mock_services):
        """Test retrieval when no subscribers exist."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.return_value = []

        response = await test_client.get('/subscribers')
        
        assert response.status_code == 200
        data = await response.get_json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_subscribers_service_error(self, test_client, mock_services):
        """Test retrieval when service throws an error."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.side_effect = Exception("Service error")

        response = await test_client.get('/subscribers')
        
        assert response.status_code == 500
        data = await response.get_json()
        assert "Failed to retrieve subscribers" in data["error"]

    @pytest.mark.asyncio
    async def test_get_subscribers_filters_incomplete_data(self, test_client, mock_services):
        """Test that subscribers with missing email or notification type are filtered out."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        incomplete_subscribers = [
            {"id": "1", "email": "user1@example.com", "notificationtype": "summary"},
            {"id": "2", "email": "", "notificationtype": "full"},  # Missing email
            {"id": "3", "email": "user3@example.com"},  # Missing notification type
            {"id": "4", "email": "user4@example.com", "notificationtype": "summary"}
        ]
        mock_entity_service.get_items.return_value = incomplete_subscribers

        response = await test_client.get('/subscribers')
        
        assert response.status_code == 200
        data = await response.get_json()
        assert len(data) == 2  # Only complete entries should be returned
        assert data[0]["email"] == "user1@example.com"
        assert data[1]["email"] == "user4@example.com"


class TestGetAllGamesEndpoint:
    """Test cases for GET /games/all endpoint."""

    @pytest.mark.asyncio
    async def test_get_all_games_success(self, test_client, mock_services, sample_games_data):
        """Test successful retrieval of all games with pagination."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        games_entries = [{"date": "2024-01-01", "scores": sample_games_data}]
        mock_entity_service.get_items.return_value = games_entries

        response = await test_client.get('/games/all?offset=0&pagesize=10')

        assert response.status_code == 200
        data = await response.get_json()
        assert data["total"] == 2
        assert data["offset"] == 0
        assert data["pagesize"] == 10
        assert len(data["games"]) == 2
        assert data["games"][0]["AwayTeam"] == "LAL"
        assert data["games"][1]["AwayTeam"] == "BOS"

    @pytest.mark.asyncio
    async def test_get_all_games_pagination(self, test_client, mock_services, sample_games_data):
        """Test pagination functionality."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        games_entries = [{"date": "2024-01-01", "scores": sample_games_data}]
        mock_entity_service.get_items.return_value = games_entries

        response = await test_client.get('/games/all?offset=1&pagesize=1')

        assert response.status_code == 200
        data = await response.get_json()
        assert data["total"] == 2
        assert data["offset"] == 1
        assert data["pagesize"] == 1
        assert len(data["games"]) == 1
        assert data["games"][0]["AwayTeam"] == "BOS"

    @pytest.mark.asyncio
    async def test_get_all_games_default_pagination(self, test_client, mock_services, sample_games_data):
        """Test default pagination values."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        games_entries = [{"date": "2024-01-01", "scores": sample_games_data}]
        mock_entity_service.get_items.return_value = games_entries

        response = await test_client.get('/games/all')

        assert response.status_code == 200
        data = await response.get_json()
        assert data["offset"] == 0
        assert data["pagesize"] == 20

    @pytest.mark.asyncio
    async def test_get_all_games_empty_result(self, test_client, mock_services):
        """Test retrieval when no games exist."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.return_value = []

        response = await test_client.get('/games/all')

        assert response.status_code == 200
        data = await response.get_json()
        assert data["total"] == 0
        assert data["games"] == []

    @pytest.mark.asyncio
    async def test_get_all_games_service_error(self, test_client, mock_services):
        """Test retrieval when service throws an error."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items.side_effect = Exception("Service error")

        response = await test_client.get('/games/all')

        assert response.status_code == 500
        data = await response.get_json()
        assert "Failed to retrieve games" in data["error"]

    @pytest.mark.asyncio
    async def test_get_all_games_handles_unexpected_format(self, test_client, mock_services):
        """Test handling of unexpected entry format."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        # Mix of valid and invalid entries
        games_entries = [
            {"date": "2024-01-01", "scores": [{"GameID": 1, "AwayTeam": "LAL"}]},
            "invalid_entry",  # This should be logged as error but not crash
            {"date": "2024-01-02", "scores": [{"GameID": 2, "AwayTeam": "BOS"}]}
        ]
        mock_entity_service.get_items.return_value = games_entries

        response = await test_client.get('/games/all')

        assert response.status_code == 200
        data = await response.get_json()
        assert data["total"] == 2  # Only valid entries counted
        assert len(data["games"]) == 2


class TestGetGamesByDateEndpoint:
    """Test cases for GET /games/<date> endpoint."""

    @pytest.mark.asyncio
    async def test_get_games_by_date_success(self, test_client, mock_services, sample_games_data):
        """Test successful retrieval of games for a specific date."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        games_entry = [{"date": "2024-01-01", "scores": sample_games_data}]
        mock_entity_service.get_items_by_condition.return_value = games_entry

        response = await test_client.get('/games/2024-01-01')

        assert response.status_code == 200
        data = await response.get_json()
        assert len(data) == 2
        assert data[0]["AwayTeam"] == "LAL"
        assert data[1]["AwayTeam"] == "BOS"

        # Verify the condition was constructed correctly
        mock_entity_service.get_items_by_condition.assert_called_once()
        call_args = mock_entity_service.get_items_by_condition.call_args
        condition = call_args[1]['condition']
        assert condition['cyoda']['conditions'][0]['value'] == "2024-01-01"
        assert condition['cyoda']['conditions'][0]['jsonPath'] == "$.date"

    @pytest.mark.asyncio
    async def test_get_games_by_date_invalid_format(self, test_client):
        """Test retrieval with invalid date format."""
        response = await test_client.get('/games/invalid-date')

        assert response.status_code == 400
        data = await response.get_json()
        assert "Invalid date format" in data["error"]

    @pytest.mark.asyncio
    async def test_get_games_by_date_no_games(self, test_client, mock_services):
        """Test retrieval when no games exist for the date."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items_by_condition.return_value = []

        response = await test_client.get('/games/2024-01-01')

        assert response.status_code == 200
        data = await response.get_json()
        assert data == []

    @pytest.mark.asyncio
    async def test_get_games_by_date_service_error(self, test_client, mock_services):
        """Test retrieval when service throws an error."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.get_items_by_condition.side_effect = Exception("Service error")

        response = await test_client.get('/games/2024-01-01')

        assert response.status_code == 500
        data = await response.get_json()
        assert "Failed to retrieve games for date" in data["error"]


class TestFetchScoresEndpoint:
    """Test cases for POST /games/fetch endpoint."""

    @pytest.mark.asyncio
    async def test_fetch_scores_success(self, test_client, mock_services, sample_fetch_request_data):
        """Test successful initiation of scores fetch."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.add_item.return_value = "fetch_request_id_123"

        response = await test_client.post('/games/fetch', json=sample_fetch_request_data)

        assert response.status_code == 202
        data = await response.get_json()
        assert "Scores fetch started" in data["message"]

        # Verify service was called with correct parameters
        mock_entity_service.add_item.assert_called_once()
        call_args = mock_entity_service.add_item.call_args
        assert call_args[1]['entity_model'] == "fetch_request"
        assert call_args[1]['entity']['api_key'] == "test_api_key"
        assert call_args[1]['entity']['start_date'] == "2024-01-01"
        assert call_args[1]['entity']['end_date'] == "2024-01-02"

    @pytest.mark.asyncio
    async def test_fetch_scores_minimal_data(self, test_client, mock_services):
        """Test fetch with only required api_key field."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.add_item.return_value = "fetch_request_id_123"

        minimal_data = {"api_key": "test_api_key"}
        response = await test_client.post('/games/fetch', json=minimal_data)

        assert response.status_code == 202
        data = await response.get_json()
        assert "Scores fetch started" in data["message"]

        # Verify optional fields are None
        call_args = mock_entity_service.add_item.call_args
        assert call_args[1]['entity']['start_date'] is None
        assert call_args[1]['entity']['end_date'] is None

    @pytest.mark.asyncio
    async def test_fetch_scores_missing_api_key(self, test_client):
        """Test fetch with missing required api_key field."""
        incomplete_data = {"start_date": "2024-01-01"}

        response = await test_client.post('/games/fetch', json=incomplete_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_fetch_scores_service_error(self, test_client, mock_services, sample_fetch_request_data):
        """Test fetch when service throws an error."""
        mock_entity_service, mock_cyoda_auth_service = mock_services
        mock_entity_service.add_item.side_effect = Exception("Service error")

        response = await test_client.post('/games/fetch', json=sample_fetch_request_data)

        assert response.status_code == 500
        data = await response.get_json()
        assert "Failed to start fetch process" in data["error"]


class TestUtilityFunctions:
    """Test cases for utility functions used in routes."""

    def test_format_email_summary(self):
        """Test email summary formatting function."""
        from routes.routes import format_email_summary

        games_data = [
            {"Day": "2024-01-01", "AwayTeam": "LAL", "HomeTeam": "GSW",
             "AwayTeamScore": 110, "HomeTeamScore": 105},
            {"Day": "2024-01-01", "AwayTeam": "BOS", "HomeTeam": "MIA",
             "AwayTeamScore": 98, "HomeTeamScore": 102}
        ]

        result = format_email_summary(games_data)

        assert "NBA Scores Summary for 2024-01-01:" in result
        assert "LAL @ GSW - 110 : 105" in result
        assert "BOS @ MIA - 98 : 102" in result

    def test_format_email_summary_empty(self):
        """Test email summary formatting with empty data."""
        from routes.routes import format_email_summary

        result = format_email_summary([])

        assert result == "NBA Scores Summary:\n"

    def test_format_email_full(self):
        """Test full email formatting function."""
        from routes.routes import format_email_full

        games_data = [
            {"Day": "2024-01-01", "AwayTeam": "LAL", "HomeTeam": "GSW",
             "AwayTeamScore": 110, "HomeTeamScore": 105, "Status": "Final",
             "Quarter": "4", "TimeRemaining": "00:00"}
        ]

        result = format_email_full(games_data)

        assert "<h1>NBA Scores for 2024-01-01</h1>" in result
        assert "<b>LAL @ GSW</b>: 110 - 105" in result
        assert "Status: Final" in result
        assert "Quarter: 4" in result

    def test_format_email_full_empty(self):
        """Test full email formatting with empty data."""
        from routes.routes import format_email_full

        result = format_email_full([])

        assert result == "<h1>NBA Scores</h1><ul></ul>"

    @pytest.mark.asyncio
    async def test_send_email_function(self):
        """Test send_email function (currently just logs)."""
        from routes.routes import send_email

        # This function currently just logs, so we test it doesn't raise exceptions
        await send_email("test@example.com", "Test Subject", "Test Body", html=False)
        await send_email("test@example.com", "Test Subject", "<p>Test Body</p>", html=True)
