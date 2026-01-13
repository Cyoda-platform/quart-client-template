"""
Integration tests for API error handling.

Tests the fixes for:
1. 404 responses from missing entity endpoints
2. Proper JSON error responses without stack traces
"""

import pytest
from unittest.mock import AsyncMock, patch

from application.app import app as application_app


@pytest.fixture
def app():
    """Get the application instance."""
    return application_app


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


class TestApplicantEndpointErrorHandling:
    """Test error handling in applicant endpoints."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_applicant_returns_404(self, client):
        """Test that getting a nonexistent applicant returns 404."""
        with patch(
            "application.routes.applicants.service.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.get("/api/applicants/nonexistent-id")
            assert response.status_code == 404
            data = await response.get_json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_missing_applicant_route_returns_404(self, client):
        """Test that missing applicant routes return 404."""
        response = await client.get("/api/applicants/missing/route/path")
        assert response.status_code == 404
        data = await response.get_json()
        assert isinstance(data, dict)
        assert "error" in data


class TestDecisionEndpointErrorHandling:
    """Test error handling in decision endpoints."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_decision_returns_404(self, client):
        """Test that getting a nonexistent decision returns 404."""
        with patch(
            "application.routes.decisions.service.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.get("/api/decisions/nonexistent-id")
            assert response.status_code == 404
            data = await response.get_json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_missing_decision_route_returns_404(self, client):
        """Test that missing decision routes return 404."""
        response = await client.get("/api/decisions/missing/route")
        assert response.status_code == 404
        data = await response.get_json()
        assert isinstance(data, dict)


class TestCreditReportEndpointErrorHandling:
    """Test error handling in credit report endpoints."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_credit_report_returns_404(self, client):
        """Test that getting a nonexistent credit report returns 404."""
        with patch(
            "application.routes.credit_reports.service.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await client.get("/api/credit-reports/nonexistent-id")
            assert response.status_code == 404
            data = await response.get_json()
            assert "error" in data

