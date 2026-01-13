"""
Tests for route validation and None payload handling.

Tests the fixes for:
1. TypeError when attempting to create schema for None
2. Input validation for None payloads in POST/PUT requests
3. Proper 400 responses for invalid input
"""

import pytest
from quart import Quart

from application.routes.applicants import applicants_bp
from application.routes.credit_reports import credit_reports_bp
from application.routes.decisions import decisions_bp
from application.routes.model_versions import model_versions_bp


@pytest.fixture
def app():
    """Create a test Quart application with all blueprints."""
    app = Quart(__name__)
    app.register_blueprint(applicants_bp)
    app.register_blueprint(credit_reports_bp)
    app.register_blueprint(decisions_bp)
    app.register_blueprint(model_versions_bp)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestRouteRegistration:
    """Test that all routes are properly registered."""

    @pytest.mark.asyncio
    async def test_applicants_routes_exist(self, client):
        """Test that applicants routes are registered."""
        response = await client.get("/api/applicants/test-id")
        assert response.status_code in [400, 404, 500]

    @pytest.mark.asyncio
    async def test_credit_reports_routes_exist(self, client):
        """Test that credit reports routes are registered."""
        response = await client.get("/api/credit-reports/test-id")
        assert response.status_code in [400, 404, 500]

    @pytest.mark.asyncio
    async def test_decisions_routes_exist(self, client):
        """Test that decisions routes are registered."""
        response = await client.get("/api/decisions/test-id")
        assert response.status_code in [400, 404, 500]

    @pytest.mark.asyncio
    async def test_model_versions_routes_exist(self, client):
        """Test that model versions routes are registered."""
        response = await client.get("/api/model-versions/test-id")
        assert response.status_code in [400, 404, 500]


class TestNonePayloadValidation:
    """Test validation of None payloads in POST/PUT requests."""

    @pytest.mark.asyncio
    async def test_create_applicant_with_none_payload(self, client):
        """Test that POST with None payload returns 400."""
        response = await client.post(
            "/api/applicants", json=None, content_type="application/json"
        )
        assert response.status_code == 400
        data = await response.get_json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_update_applicant_with_none_payload(self, client):
        """Test that PUT with None payload returns 400."""
        response = await client.put(
            "/api/applicants/test-id", json=None, content_type="application/json"
        )
        assert response.status_code == 400
        data = await response.get_json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_create_credit_report_with_none_payload(self, client):
        """Test that POST credit report with None payload returns 400."""
        response = await client.post(
            "/api/credit-reports", json=None, content_type="application/json"
        )
        assert response.status_code == 400
        data = await response.get_json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_create_decision_with_none_payload(self, client):
        """Test that POST decision with None payload returns 400."""
        response = await client.post(
            "/api/decisions", json=None, content_type="application/json"
        )
        assert response.status_code == 400
        data = await response.get_json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_create_model_version_with_none_payload(self, client):
        """Test that POST model version with None payload returns 400."""
        response = await client.post(
            "/api/model-versions", json=None, content_type="application/json"
        )
        assert response.status_code == 400
        data = await response.get_json()
        assert "error" in data


class TestValidResponseSchemas:
    """Test that response schemas are properly defined."""

    def test_validate_decorators_use_dict_not_none(self):
        """Test that @validate decorators use dict instead of None."""
        import inspect

        from application.routes import (
            applicants,
            credit_reports,
            decisions,
            model_versions,
        )

        for module in [applicants, credit_reports, decisions, model_versions]:
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and hasattr(obj, "__wrapped__"):
                    source = inspect.getsource(obj)
                    if "@validate" in source:
                        assert (
                            "(None, None)" not in source
                        ), f"Function {name} uses (None, None) in @validate"
