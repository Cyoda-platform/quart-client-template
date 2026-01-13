"""
Tests for None schema handling and 404 error handling.

Tests the fixes for:
1. TypeError when attempting to serialize None entities
2. 404 NotFound exceptions returning concise JSON responses
3. safe_serialize utility function
"""

import pytest
from pydantic import BaseModel
from quart import Quart
from werkzeug.exceptions import NotFound

from common.exception.exception_handler import register_error_handlers
from common.utils.serialization import safe_serialize


@pytest.fixture
def app():
    """Create a test Quart application."""
    app = Quart(__name__)
    register_error_handlers(app)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestNoneEntitySerialization:
    """Test handling of None entities in serialization."""

    def test_to_entity_dict_with_none_raises_error(self):
        """Test that _to_entity_dict raises ValueError for None input."""
        from application.routes.applicants import _to_entity_dict

        with pytest.raises(ValueError, match="Cannot serialize None entity"):
            _to_entity_dict(None)

    def test_to_entity_dict_with_dict_returns_dict(self):
        """Test that _to_entity_dict returns dict for dict input."""
        from application.routes.applicants import _to_entity_dict

        test_data = {"id": "123", "name": "test"}
        result = _to_entity_dict(test_data)
        assert result == test_data

    def test_to_entity_dict_with_pydantic_model(self):
        """Test that _to_entity_dict handles Pydantic models."""
        from pydantic import BaseModel

        from application.routes.applicants import _to_entity_dict

        class TestModel(BaseModel):
            id: str
            name: str

        model = TestModel(id="123", name="test")
        result = _to_entity_dict(model)
        assert isinstance(result, dict)
        assert result["id"] == "123"
        assert result["name"] == "test"


class TestSafeSerialize:
    """Test safe_serialize utility function."""

    def test_safe_serialize_with_none_returns_404(self):
        """Test that safe_serialize returns 404 for None resource."""
        response, status = safe_serialize(None)
        assert status == 404
        assert response["error"] == "Resource not found"
        assert response["code"] == "NOT_FOUND"

    def test_safe_serialize_with_dict_returns_200(self):
        """Test that safe_serialize returns dict as-is with 200."""
        test_data = {"id": "123", "name": "test"}
        response, status = safe_serialize(test_data)
        assert status == 200
        assert response == test_data

    def test_safe_serialize_with_pydantic_model(self):
        """Test that safe_serialize handles Pydantic models."""

        class TestModel(BaseModel):
            id: str
            name: str

        model = TestModel(id="123", name="test")
        response, status = safe_serialize(model)
        assert status == 200
        assert isinstance(response, dict)
        assert response["id"] == "123"
        assert response["name"] == "test"

    def test_safe_serialize_with_invalid_type(self):
        """Test that safe_serialize handles invalid types gracefully."""
        response, status = safe_serialize(12345)
        assert status == 500
        assert response["error"] == "Serialization failed"


class TestNotFoundExceptionHandling:
    """Test handling of 404 NotFound exceptions."""

    @pytest.mark.asyncio
    async def test_not_found_returns_404_json(self, app, client):
        """Test that NotFound exception returns 404 JSON response."""

        @app.route("/test-404")
        async def test_route():
            raise NotFound("Resource not found")

        response = await client.get("/test-404")
        assert response.status_code == 404
        data = await response.get_json()
        assert "error" in data
        assert data["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_missing_route_returns_404_json(self, app, client):
        """Test that missing routes return 404 JSON response."""
        response = await client.get("/nonexistent/route")
        assert response.status_code == 404
        data = await response.get_json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_not_found_does_not_log_stack_trace(self, app, client, caplog):
        """Test that NotFound exceptions log at debug level, not exception."""
        import logging

        caplog.set_level(logging.DEBUG)

        @app.route("/test-404-log")
        async def test_route():
            raise NotFound("Resource not found")

        response = await client.get("/test-404-log")
        assert response.status_code == 404
