"""
Integration tests for API error handling.

Tests the fixes for:
1. 404 responses from missing routes
2. Proper JSON error responses without stack traces
"""

import pytest
from quart import Quart
from werkzeug.exceptions import NotFound

from common.exception.exception_handler import register_error_handlers


@pytest.fixture
def app():
    """Create a test application with error handlers."""
    app = Quart(__name__)
    register_error_handlers(app)

    @app.route("/api/test-404")
    async def test_404():
        raise NotFound("Resource not found")

    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestNotFoundErrorHandling:
    """Test 404 error handling in API endpoints."""

    @pytest.mark.asyncio
    async def test_explicit_not_found_returns_404_json(self, client):
        """Test that explicit NotFound raises return 404 JSON."""
        response = await client.get("/api/test-404")
        assert response.status_code == 404
        data = await response.get_json()
        assert isinstance(data, dict)
        assert "error" in data
        assert data["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_missing_route_returns_404_json(self, client):
        """Test that missing routes return 404 JSON."""
        response = await client.get("/api/nonexistent/route")
        assert response.status_code == 404
        data = await response.get_json()
        assert isinstance(data, dict)
        assert "error" in data

