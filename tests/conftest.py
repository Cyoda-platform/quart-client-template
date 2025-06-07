# ABOUTME: Pytest configuration and shared fixtures for testing
# ABOUTME: Provides mock services and test client setup for route testing

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from quart import Quart
from quart.testing import QuartClient

from app import app
from routes.routes import routes_bp


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_app():
    """Create a test application instance."""
    test_app = Quart(__name__)
    test_app.register_blueprint(routes_bp)
    return test_app


@pytest.fixture
async def test_client(test_app):
    """Create a test client for the application."""
    return test_app.test_client()


@pytest.fixture
def mock_entity_service():
    """Mock entity service for testing."""
    mock_service = AsyncMock()
    mock_service.add_item = AsyncMock()
    mock_service.get_items = AsyncMock()
    mock_service.get_items_by_condition = AsyncMock()
    mock_service.delete_item = AsyncMock()
    mock_service.update_item = AsyncMock()
    return mock_service


@pytest.fixture
def mock_cyoda_auth_service():
    """Mock Cyoda auth service for testing."""
    mock_auth = AsyncMock()
    mock_auth.get_bearer_token = AsyncMock(return_value="mock_token")
    return mock_auth


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for external API calls."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    return mock_client, mock_response


@pytest.fixture(autouse=True)
def mock_services(mock_entity_service, mock_cyoda_auth_service):
    """Auto-use fixture to mock all services in routes module."""
    with patch('routes.routes.entity_service', mock_entity_service), \
         patch('routes.routes.cyoda_auth_service', mock_cyoda_auth_service):
        yield mock_entity_service, mock_cyoda_auth_service


@pytest.fixture
def sample_subscriber_data():
    """Sample subscriber data for testing."""
    return {
        "email": "test@example.com",
        "notificationType": "summary"
    }


@pytest.fixture
def sample_fetch_request_data():
    """Sample fetch request data for testing."""
    return {
        "api_key": "test_api_key",
        "start_date": "2024-01-01",
        "end_date": "2024-01-02"
    }


@pytest.fixture
def sample_games_data():
    """Sample NBA games data for testing."""
    return [
        {
            "GameID": 1,
            "Day": "2024-01-01",
            "AwayTeam": "LAL",
            "HomeTeam": "GSW",
            "AwayTeamScore": 110,
            "HomeTeamScore": 105,
            "Status": "Final",
            "Quarter": "4",
            "TimeRemaining": "00:00"
        },
        {
            "GameID": 2,
            "Day": "2024-01-01",
            "AwayTeam": "BOS",
            "HomeTeam": "MIA",
            "AwayTeamScore": 98,
            "HomeTeamScore": 102,
            "Status": "Final",
            "Quarter": "4",
            "TimeRemaining": "00:00"
        }
    ]


@pytest.fixture
def sample_subscribers_list():
    """Sample list of subscribers for testing."""
    return [
        {
            "id": "1",
            "email": "user1@example.com",
            "notificationtype": "summary"
        },
        {
            "id": "2", 
            "email": "user2@example.com",
            "notificationtype": "full"
        }
    ]
