"""
Unit tests for CyodaRepository.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.repository.cyoda.cyoda_repository import CyodaRepository


class MockCyodaAuthService:
    """Mock Cyoda authentication service."""

    async def get_access_token(self) -> str:
        """Return a mock access token."""
        return "mock-token-123"

    def invalidate_tokens(self) -> None:
        """Invalidate tokens."""
        pass


class TestCyodaRepository:
    """Test suite for CyodaRepository."""

    @pytest.fixture
    def auth_service(self):
        """Create a mock auth service."""
        return MockCyodaAuthService()

    @pytest.fixture
    def repository(self, auth_service):
        """Create a CyodaRepository instance."""
        # Reset singleton
        CyodaRepository._instance = None
        return CyodaRepository(auth_service)

    @pytest.fixture
    def sample_entity_data(self):
        """Create sample entity data."""
        return {
            "name": "Test Entity",
            "value": 42,
            "status": "active",
            "technical_id": "test-id-123",
        }

    @pytest.fixture
    def sample_meta(self):
        """Create sample metadata."""
        return {
            "token": "test-token",
            "entity_model": "TestEntity",
            "entity_version": "1",
        }

    # Singleton Pattern Tests

    def test_singleton_pattern(self, auth_service):
        """Test that CyodaRepository follows singleton pattern."""
        CyodaRepository._instance = None
        repo1 = CyodaRepository(auth_service)
        repo2 = CyodaRepository(auth_service)

        assert repo1 is repo2

    def test_singleton_thread_safety(self, auth_service):
        """Test singleton is thread-safe."""
        import threading

        CyodaRepository._instance = None
        instances = []

        def create_instance():
            instances.append(CyodaRepository(auth_service))

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All instances should be the same
        assert all(inst is instances[0] for inst in instances)

    # Helper Method Tests

    def test_json_loads_or_empty_valid_json(self, repository):
        """Test JSON parsing with valid JSON."""
        result = repository._json_loads_or_empty('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_loads_or_empty_invalid_json(self, repository):
        """Test JSON parsing with invalid JSON."""
        result = repository._json_loads_or_empty("not valid json")
        assert result == {}

    def test_json_loads_or_empty_non_dict(self, repository):
        """Test JSON parsing with non-dict result."""
        result = repository._json_loads_or_empty('["array"]')
        assert result == {}

    def test_json_loads_or_empty_empty_string(self, repository):
        """Test JSON parsing with empty string."""
        result = repository._json_loads_or_empty("")
        assert result == {}

    def test_extract_technical_id_from_result_valid(self, repository):
        """Test extracting technical ID from valid result."""
        result = [{"entityIds": ["id-123", "id-456"]}]
        tech_id = repository._extract_technical_id_from_result(result)
        assert tech_id == "id-123"

    def test_extract_technical_id_from_result_empty_list(self, repository):
        """Test extracting technical ID from empty list."""
        result = []
        tech_id = repository._extract_technical_id_from_result(result)
        assert tech_id is None

    def test_extract_technical_id_from_result_no_entity_ids(self, repository):
        """Test extracting technical ID when entityIds is missing."""
        result = [{"other": "data"}]
        tech_id = repository._extract_technical_id_from_result(result)
        assert tech_id is None

    def test_extract_technical_id_from_result_empty_entity_ids(self, repository):
        """Test extracting technical ID when entityIds is empty."""
        result = [{"entityIds": []}]
        tech_id = repository._extract_technical_id_from_result(result)
        assert tech_id is None

    def test_coerce_list_of_dicts_valid(self, repository):
        """Test coercing valid list of dicts."""
        value = [{"a": 1}, {"b": 2}]
        result = repository._coerce_list_of_dicts(value)
        assert result == [{"a": 1}, {"b": 2}]

    def test_coerce_list_of_dicts_mixed(self, repository):
        """Test coercing list with mixed types."""
        value = [{"a": 1}, "string", {"b": 2}, 123]
        result = repository._coerce_list_of_dicts(value)
        assert result == [{"a": 1}, {"b": 2}]

    def test_coerce_list_of_dicts_not_list(self, repository):
        """Test coercing non-list value."""
        value = {"a": 1}
        result = repository._coerce_list_of_dicts(value)
        assert result == []

    def test_ensure_technical_id_on_entities_with_id(self, repository):
        """Test ensuring technical_id when already present."""
        entities = [{"technical_id": "id-1", "name": "Test"}]
        result = repository._ensure_technical_id_on_entities(entities)
        assert result[0]["technical_id"] == "id-1"

    def test_ensure_technical_id_on_entities_from_meta(self, repository):
        """Test ensuring technical_id from meta.id."""
        entities = [{"name": "Test", "meta": {"id": "meta-id-1"}}]
        result = repository._ensure_technical_id_on_entities(entities)
        assert result[0]["technical_id"] == "meta-id-1"

    def test_ensure_technical_id_on_entities_from_id_field(self, repository):
        """Test ensuring technical_id from id field."""
        entities = [{"name": "Test", "id": "id-1"}]
        result = repository._ensure_technical_id_on_entities(entities)
        assert result[0]["technical_id"] == "id-1"

    def test_ensure_technical_id_on_entities_empty_technical_id(self, repository):
        """Test ensuring technical_id when it's empty."""
        entities = [{"technical_id": "", "name": "Test", "id": "id-1"}]
        result = repository._ensure_technical_id_on_entities(entities)
        assert result[0]["technical_id"] == "id-1"

    # CRUD Operation Tests

    @pytest.mark.asyncio
    async def test_find_by_id_success(
        self, repository, sample_meta, sample_entity_data
    ):
        """Test finding entity by ID successfully."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"data": sample_entity_data, "meta": {"state": "active"}},
                "status": 200,
            }

            result = await repository.find_by_id(sample_meta, "test-id-123")

            assert result is not None
            assert result["technical_id"] == "test-id-123"
            assert result["current_state"] == "active"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, repository, sample_meta):
        """Test finding entity by ID when not found."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {},
                "status": 404,
            }

            result = await repository.find_by_id(sample_meta, "non-existent")

            assert result is None

    @pytest.mark.asyncio
    async def test_find_by_id_with_non_dict_json(self, repository, sample_meta):
        """Test finding entity by ID when JSON is not a dict."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": "not a dict",
                "status": 200,
            }

            result = await repository.find_by_id(sample_meta, "test-id")

            # Returns None when json is not a dict
            assert result is None

    @pytest.mark.asyncio
    async def test_find_all_success(self, repository, sample_meta):
        """Test finding all entities successfully."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [
                    {"name": "Entity 1", "id": "id-1"},
                    {"name": "Entity 2", "id": "id-2"},
                ],
                "status": 200,
            }

            result = await repository.find_all(sample_meta)

            assert len(result) == 2
            assert result[0]["id"] == "id-1"
            assert result[1]["id"] == "id-2"

    @pytest.mark.asyncio
    async def test_find_all_empty(self, repository, sample_meta):
        """Test finding all entities when empty."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [],
                "status": 200,
            }

            result = await repository.find_all(sample_meta)

            assert result == []

    @pytest.mark.asyncio
    async def test_find_all_by_criteria_success(self, repository, sample_meta):
        """Test finding entities by criteria successfully."""
        with patch.object(
            repository, "_send_search_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"name": "Test", "id": "id-1"}],
                "status": 200,
            }

            criteria = {"name": "Test"}
            result = await repository.find_all_by_criteria(sample_meta, criteria)

            assert len(result) == 1
            assert result[0]["technical_id"] == "id-1"

    @pytest.mark.asyncio
    async def test_save_success(self, repository, sample_meta, sample_entity_data):
        """Test saving entity successfully."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"entityIds": ["new-id-123"]}],
                "status": 200,
            }

            result = await repository.save(sample_meta, sample_entity_data)

            assert result == "new-id-123"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_error(self, repository, sample_meta, sample_entity_data):
        """Test saving entity with error."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"errorMessage": "Save failed"},
                "status": 500,
            }

            result = await repository.save(sample_meta, sample_entity_data)

            # Returns None when extraction fails
            assert result is None

    @pytest.mark.asyncio
    async def test_update_success(self, repository, sample_meta, sample_entity_data):
        """Test updating entity successfully using loopback endpoint (no transition)."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": ["test-id-123"]},
                "status": 200,
            }

            result = await repository.update(
                sample_meta, "test-id-123", sample_entity_data
            )

            assert result == "test-id-123"
            # No update_transition in meta — must use loopback path (no transition segment)
            called_path = mock_request.call_args.kwargs["path"]
            assert "test-id-123" in called_path
            assert called_path.startswith("entity/JSON/test-id-123?")

    @pytest.mark.asyncio
    async def test_update_uses_transition_path_when_specified(
        self, repository, sample_meta, sample_entity_data
    ):
        """Test that update uses the transition path when update_transition is in meta."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": ["test-id-123"]},
                "status": 200,
            }

            meta_with_transition = {**sample_meta, "update_transition": "my_transition"}
            result = await repository.update(
                meta_with_transition, "test-id-123", sample_entity_data
            )

            assert result == "test-id-123"
            called_path = mock_request.call_args.kwargs["path"]
            assert "entity/JSON/test-id-123/my_transition" in called_path

    @pytest.mark.asyncio
    async def test_update_with_transition(self, repository, sample_meta):
        """Test updating entity with workflow transition."""
        with patch.object(
            repository, "_launch_transition", new_callable=AsyncMock
        ) as mock_transition:
            mock_transition.return_value = None

            meta_with_transition = {**sample_meta, "transition": "approve"}
            result = await repository.update(meta_with_transition, "test-id-123", None)

            # When entity is None, it launches transition and returns None
            assert result is None
            mock_transition.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_id_success(self, repository, sample_meta):
        """Test deleting entity by ID successfully."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"success": True},
                "status": 200,
            }

            await repository.delete_by_id(sample_meta, "test-id-123")

            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_by_id_error(self, repository, sample_meta):
        """Test deleting entity by ID with error."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"errorMessage": "Delete failed"},
                "status": 500,
            }

            # Should not raise exception
            await repository.delete_by_id(sample_meta, "test-id-123")

    @pytest.mark.asyncio
    async def test_count_success(self, repository, sample_meta):
        """Test counting entities successfully."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [
                    {"name": "Entity 1", "id": "id-1"},
                    {"name": "Entity 2", "id": "id-2"},
                ],
                "status": 200,
            }

            result = await repository.count(sample_meta)

            assert result == 2

    @pytest.mark.asyncio
    async def test_exists_by_key_true(self, repository, sample_meta):
        """Test checking entity existence when it exists."""
        with patch.object(
            repository, "find_by_key", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = {"name": "Test", "id": "id-1"}

            result = await repository.exists_by_key(sample_meta, "id-1")

            assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_key_false(self, repository, sample_meta):
        """Test checking entity existence when it doesn't exist."""
        with patch.object(
            repository, "find_by_key", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = None

            result = await repository.exists_by_key(sample_meta, "non-existent")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_entity_count_success(self, repository, sample_meta):
        """Test getting entity count successfully."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"count": 42},
                "status": 200,
            }

            result = await repository.get_entity_count(sample_meta)

            assert result == 42

    @pytest.mark.asyncio
    async def test_get_entity_count_with_point_in_time(self, repository, sample_meta):
        """Test getting entity count at specific point in time."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"count": 30},
                "status": 200,
            }

            point_in_time = datetime(2024, 1, 1, 12, 0, 0)
            result = await repository.get_entity_count(sample_meta, point_in_time)

            assert result == 30

    @pytest.mark.asyncio
    async def test_get_entity_changes_metadata_success(self, repository):
        """Test getting entity change history metadata."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [
                    {"changeType": "created", "timestamp": "2024-01-01T00:00:00Z"},
                    {"changeType": "updated", "timestamp": "2024-01-02T00:00:00Z"},
                ],
                "status": 200,
            }

            result = await repository.get_entity_changes_metadata("test-id-123")

            assert len(result) == 2
            assert result[0]["changeType"] == "created"

    @pytest.mark.asyncio
    async def test_get_meta_success(self, repository):
        """Test getting repository metadata."""
        result = await repository.get_meta("test-token", "TestEntity", "1")

        assert result["token"] == "test-token"
        assert result["entity_model"] == "TestEntity"
        assert result["entity_version"] == "1"

    @pytest.mark.asyncio
    async def test_save_all_success(self, repository, sample_meta):
        """Test saving multiple entities successfully."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"entityIds": ["id-1", "id-2"]}],
                "status": 200,
            }

            entities = [
                {"name": "Entity 1", "value": 10},
                {"name": "Entity 2", "value": 20},
            ]
            result = await repository.save_all(sample_meta, entities)

            # Returns the first technical_id
            assert result == "id-1"

    @pytest.mark.asyncio
    async def test_delete_all_success(self, repository, sample_meta):
        """Test deleting all entities successfully."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"success": True},
                "status": 200,
            }

            await repository.delete_all(sample_meta)

            # Should call delete once for the entire entity type
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_id_at_time_success(
        self, repository, sample_meta, sample_entity_data
    ):
        """Test finding entity by ID at specific point in time."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": sample_entity_data,
                "status": 200,
            }

            point_in_time = datetime(2024, 1, 1, 12, 0, 0)
            result = await repository.find_by_id(
                sample_meta, "test-id-123", point_in_time
            )

            assert result is not None
            assert result["technical_id"] == "test-id-123"

    @pytest.mark.asyncio
    async def test_find_all_by_criteria_at_time(self, repository, sample_meta):
        """Test finding entities by criteria at specific point in time."""
        with patch.object(
            repository, "_send_search_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"name": "Test", "id": "id-1"}],
                "status": 200,
            }

            point_in_time = datetime(2024, 1, 1, 12, 0, 0)
            criteria = {"name": "Test"}
            result = await repository.find_all_by_criteria(
                sample_meta, criteria, point_in_time
            )

            assert len(result) == 1

    # Additional Edge Cases and Error Handling Tests

    @pytest.mark.asyncio
    async def test_find_by_id_with_empty_response(self, repository, sample_meta):
        """Test finding entity by ID with empty response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {},
                "status": 200,
            }

            result = await repository.find_by_id(sample_meta, "test-id")

            # Empty response still returns a dict with technical_id
            assert result is not None
            assert result["technical_id"] == "test-id"

    @pytest.mark.asyncio
    async def test_find_all_with_non_list_response(self, repository, sample_meta):
        """Test finding all entities with non-list response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"error": "Invalid response"},
                "status": 200,
            }

            result = await repository.find_all(sample_meta)

            assert result == []

    @pytest.mark.asyncio
    async def test_save_with_empty_entity(self, repository, sample_meta):
        """Test saving empty entity."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"entityIds": ["new-id"]}],
                "status": 200,
            }

            result = await repository.save(sample_meta, {})

            assert result == "new-id"

    @pytest.mark.asyncio
    async def test_update_with_none_entity(self, repository, sample_meta):
        """Test updating with None entity (transition only)."""
        with patch.object(
            repository, "_launch_transition", new_callable=AsyncMock
        ) as mock_transition:
            mock_transition.return_value = None

            meta_with_transition = {**sample_meta, "transition": "approve"}
            result = await repository.update(meta_with_transition, "test-id", None)

            assert result is None
            mock_transition.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_entity_count_zero(self, repository, sample_meta):
        """Test getting entity count when zero."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"count": 0},
                "status": 200,
            }

            result = await repository.get_entity_count(sample_meta)

            assert result == 0

    @pytest.mark.asyncio
    async def test_get_entity_changes_metadata_empty(self, repository):
        """Test getting entity change history when empty."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [],
                "status": 200,
            }

            result = await repository.get_entity_changes_metadata("test-id")

            assert result == []

    @pytest.mark.asyncio
    async def test_save_all_with_empty_list(self, repository, sample_meta):
        """Test saving empty list of entities."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"entityIds": []}],
                "status": 200,
            }

            result = await repository.save_all(sample_meta, [])

            assert result is None

    @pytest.mark.asyncio
    async def test_find_all_404_response(self, repository, sample_meta):
        """Test find_all with 404 response returns empty list."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"error": "Not found"},
                "status": 404,
            }

            result = await repository.find_all(sample_meta)

            assert result == []

    @pytest.mark.asyncio
    async def test_find_all_by_criteria_non_200_response(self, repository, sample_meta):
        """Test find_all_by_criteria with non-200 response returns empty list."""
        with patch.object(
            repository, "_send_search_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                "json": {"error": "Bad request"},
                "status": 400,
            }

            criteria = {"name": "Test"}
            result = await repository.find_all_by_criteria(sample_meta, criteria)

            assert result == []

    @pytest.mark.asyncio
    async def test_update_non_200_response_returns_none(self, repository, sample_meta):
        """Test update with non-200 response returns None."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"error": "Update failed"},
                "status": 400,
            }

            result = await repository.update(
                sample_meta, "test-id", {"name": "Updated"}
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_search_completion_timeout(self, repository):
        """Test _wait_for_search_completion raises TimeoutError on timeout."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            # Always return RUNNING status
            mock_request.return_value = {
                "json": {"snapshotStatus": "RUNNING"},
                "status": 200,
            }

            with pytest.raises(TimeoutError) as exc_info:
                await repository._wait_for_search_completion(
                    "snapshot-123", timeout=0.1, interval=0.05
                )

            assert "Timeout exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_wait_for_search_completion_failed_status(self, repository):
        """Test _wait_for_search_completion raises exception on failed status."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"snapshotStatus": "FAILED", "error": "Snapshot failed"},
                "status": 200,
            }

            with pytest.raises(Exception) as exc_info:
                await repository._wait_for_search_completion("snapshot-123")

            assert "Snapshot search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_wait_for_search_completion_non_200_response(self, repository):
        """Test _wait_for_search_completion returns early on non-200 response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"error": "Not found"},
                "status": 404,
            }

            # Should return without raising
            result = await repository._wait_for_search_completion("snapshot-123")
            assert result is None

    @pytest.mark.asyncio
    async def test_send_search_request_retry_on_401(self, repository):
        """Test _send_search_request retries on 401 and invalidates token."""
        # Mock the auth service to track token invalidation
        invalidate_called = False
        original_invalidate = repository._cyoda_auth_service.invalidate_tokens

        def track_invalidate():
            nonlocal invalidate_called
            invalidate_called = True
            original_invalidate()

        repository._cyoda_auth_service.invalidate_tokens = track_invalidate

        with patch("common.utils.utils.send_request") as mock_request:
            # First call returns 401, second call succeeds
            mock_request.side_effect = [
                {"json": {"error": "Unauthorized"}, "status": 401},
                {"json": [{"name": "Test"}], "status": 200},
            ]

            result = await repository._send_search_request(
                method="post", path="search/TestEntity/1", data="{}"
            )

            assert result["status"] == 200
            assert mock_request.call_count == 2
            assert invalidate_called

    @pytest.mark.asyncio
    async def test_send_search_request_max_retries_exceeded(self, repository):
        """Test _send_search_request returns 401 response after retry (doesn't raise)."""
        with patch("common.utils.utils.send_request") as mock_request:
            # Always return 401
            mock_request.return_value = {
                "json": {"error": "Unauthorized"},
                "status": 401,
            }

            # The method returns the 401 response on second attempt, doesn't raise
            result = await repository._send_search_request(
                method="post", path="search/TestEntity/1", data="{}"
            )

            assert result["status"] == 401
            assert mock_request.call_count == 2  # Initial + 1 retry

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_lifecycle_condition(self, repository):
        """Test _ensure_cyoda_format with lifecycle condition."""
        criteria = {
            "type": "lifecycle",
            "field": "state",
            "operatorType": "EQUALS",
            "value": "VALIDATED",
        }

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "lifecycle"

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_state_field(self, repository):
        """Test _ensure_cyoda_format converts state field to lifecycle condition."""
        criteria = {"state": "VALIDATED"}

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "lifecycle"
        assert result["conditions"][0]["field"] == "state"
        assert result["conditions"][0]["value"] == "VALIDATED"

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_current_state_field(self, repository):
        """Test _ensure_cyoda_format converts current_state field to lifecycle condition."""
        criteria = {"current_state": "ACTIVE"}

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "lifecycle"
        assert result["conditions"][0]["field"] == "current_state"

    @pytest.mark.asyncio
    async def test_find_by_id_with_state_in_meta(self, repository, sample_meta):
        """Test finding entity by ID with state in meta."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {
                    "data": {"name": "Test", "value": 10},
                    "meta": {"state": "validated", "id": "test-id"},
                },
                "status": 200,
            }

            result = await repository.find_by_id(sample_meta, "test-id")

            assert result is not None
            assert result["current_state"] == "validated"
            assert result["technical_id"] == "test-id"

    @pytest.mark.asyncio
    async def test_find_by_id_extracts_transaction_id_from_meta(
        self, repository, sample_meta
    ):
        """Test that transactionId from meta is extracted as transaction_id."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {
                    "data": {"name": "Test"},
                    "meta": {
                        "state": "active",
                        "id": "test-id",
                        "transactionId": "txn-uuid-123",
                    },
                },
                "status": 200,
            }

            result = await repository.find_by_id(sample_meta, "test-id")

            assert result is not None
            assert result["transaction_id"] == "txn-uuid-123"

    @pytest.mark.asyncio
    async def test_find_by_id_transaction_id_none_when_missing(
        self, repository, sample_meta
    ):
        """Test that transaction_id is None when transactionId absent from meta."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {
                    "data": {"name": "Test"},
                    "meta": {"state": "active", "id": "test-id"},
                },
                "status": 200,
            }

            result = await repository.find_by_id(sample_meta, "test-id")

            assert result is not None
            assert result["transaction_id"] is None

    @pytest.mark.asyncio
    async def test_ensure_technical_id_priority(self, repository):
        """Test technical_id priority: technical_id > meta.id > id."""
        entities = [
            {"technical_id": "tech-1", "meta": {"id": "meta-1"}, "id": "id-1"},
            {"meta": {"id": "meta-2"}, "id": "id-2"},
            {"id": "id-3"},
        ]

        result = repository._ensure_technical_id_on_entities(entities)

        assert result[0]["technical_id"] == "tech-1"
        assert result[1]["technical_id"] == "meta-2"
        assert result[2]["technical_id"] == "id-3"

    # Search and Criteria Tests

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_already_group(self, repository):
        """Test _ensure_cyoda_format with already formatted group."""
        criteria = {
            "type": "group",
            "operator": "AND",
            "conditions": [
                {
                    "type": "simple",
                    "jsonPath": "$.name",
                    "operatorType": "EQUALS",
                    "value": "Test",
                }
            ],
        }

        result = repository._ensure_cyoda_format(criteria)

        assert result == criteria
        assert result["type"] == "group"

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_single_simple_condition(self, repository):
        """Test _ensure_cyoda_format with single simple condition."""
        criteria = {
            "type": "simple",
            "jsonPath": "$.name",
            "operatorType": "EQUALS",
            "value": "Test",
        }

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 1
        assert result["conditions"][0] == criteria

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_single_lifecycle_condition(self, repository):
        """Test _ensure_cyoda_format with single lifecycle condition."""
        criteria = {
            "type": "lifecycle",
            "field": "state",
            "operatorType": "EQUALS",
            "value": "VALIDATED",
        }

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 1
        assert result["conditions"][0]["type"] == "lifecycle"

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_dict_with_operators(self, repository):
        """Test _ensure_cyoda_format with dict containing operators."""
        criteria = {
            "name": {"eq": "Test"},
            "value": {"gt": 10},
            "status": {"contains": "active"},
        }

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 3

        # Check operator mapping
        name_condition = next(
            c for c in result["conditions"] if c["jsonPath"] == "$.name"
        )
        assert name_condition["operatorType"] == "EQUALS"
        assert name_condition["value"] == "Test"

        value_condition = next(
            c for c in result["conditions"] if c["jsonPath"] == "$.value"
        )
        assert value_condition["operatorType"] == "GREATER_THAN"
        assert value_condition["value"] == 10

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_simple_field_value(self, repository):
        """Test _ensure_cyoda_format with simple field-value pairs."""
        criteria = {"name": "Test", "status": "active"}

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 2

        # All should use EQUALS operator
        for condition in result["conditions"]:
            assert condition["operatorType"] == "EQUALS"

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_with_json_path(self, repository):
        """Test _ensure_cyoda_format with existing jsonPath."""
        criteria = {"$.custom.field": "value"}

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        # Should preserve the jsonPath format
        assert any("$.custom.field" in c["jsonPath"] for c in result["conditions"])

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_non_dict(self, repository):
        """Test _ensure_cyoda_format with non-dict input."""
        criteria = "not a dict"

        result = repository._ensure_cyoda_format(criteria)

        # Should return as-is
        assert result == criteria

    @pytest.mark.asyncio
    async def test_ensure_cyoda_format_with_all_operators(self, repository):
        """Test _ensure_cyoda_format with various operators."""
        criteria = {
            "field1": {"eq": "value1"},
            "field2": {"ieq": "value2"},
            "field3": {"ne": "value3"},
            "field4": {"contains": "value4"},
            "field5": {"icontains": "value5"},
            "field6": {"gt": 100},
            "field7": {"lt": 50},
            "field8": {"gte": 10},
            "field9": {"lte": 90},
            "field10": {"startswith": "prefix"},
            "field11": {"endswith": "suffix"},
            "field12": {"in": ["a", "b", "c"]},
            "field13": {"not_in": ["x", "y"]},
        }

        result = repository._ensure_cyoda_format(criteria)

        assert result["type"] == "group"
        assert len(result["conditions"]) == 13

        # Verify operator mappings
        operator_map = {
            "field1": "EQUALS",
            "field2": "IEQUALS",
            "field3": "NOT_EQUALS",
            "field4": "CONTAINS",
            "field5": "ICONTAINS",
            "field6": "GREATER_THAN",
            "field7": "LESS_THAN",
            "field8": "GREATER_THAN_OR_EQUAL",
            "field9": "LESS_THAN_OR_EQUAL",
            "field10": "STARTS_WITH",
            "field11": "ENDS_WITH",
            "field12": "IN",
            "field13": "NOT_IN",
        }

        for field, expected_op in operator_map.items():
            condition = next(
                c for c in result["conditions"] if f"$.{field}" in c["jsonPath"]
            )
            assert condition["operatorType"] == expected_op

    # Edge Message Tests

    @pytest.mark.asyncio
    async def test_find_by_id_edge_message_cached(self, repository, sample_meta):
        """Test finding edge message by ID from cache."""
        from common.repository.cyoda.cyoda_repository import (
            CYODA_ENTITY_TYPE_EDGE_MESSAGE,
            _edge_messages_cache,
        )

        # Clear cache first
        _edge_messages_cache.clear()

        # Add to cache
        cached_data = {"message": "cached content"}
        _edge_messages_cache["msg-123"] = cached_data

        meta_with_type = {**sample_meta, "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE}

        result = await repository.find_by_id(meta_with_type, "msg-123")

        assert result == cached_data

    @pytest.mark.asyncio
    async def test_find_by_id_edge_message_from_api(self, repository, sample_meta):
        """Test finding edge message by ID from API."""
        from common.repository.cyoda.cyoda_repository import (
            CYODA_ENTITY_TYPE_EDGE_MESSAGE,
            _edge_messages_cache,
        )

        # Clear cache
        _edge_messages_cache.clear()

        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"content": '{"edge_message_content": {"message": "test"}}'},
                "status": 200,
            }

            meta_with_type = {**sample_meta, "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE}

            result = await repository.find_by_id(meta_with_type, "msg-456")

            assert result == {"message": "test"}
            # Should be cached now
            assert "msg-456" in _edge_messages_cache

    @pytest.mark.asyncio
    async def test_find_by_id_edge_message_no_content(self, repository, sample_meta):
        """Test finding edge message with no content."""
        from common.repository.cyoda.cyoda_repository import (
            CYODA_ENTITY_TYPE_EDGE_MESSAGE,
            _edge_messages_cache,
        )

        _edge_messages_cache.clear()

        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"content": "{}"},
                "status": 200,
            }

            meta_with_type = {**sample_meta, "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE}

            result = await repository.find_by_id(meta_with_type, "msg-789")

            assert result is None

    @pytest.mark.asyncio
    async def test_save_edge_message(self, repository, sample_meta):
        """Test saving edge message."""
        from common.repository.cyoda.cyoda_repository import (
            CYODA_ENTITY_TYPE_EDGE_MESSAGE,
        )

        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"entityIds": ["msg-new-123"]}],
                "status": 200,
            }

            meta_with_type = {
                **sample_meta,
                "type": CYODA_ENTITY_TYPE_EDGE_MESSAGE,
                "entity_model": "TestMessage",
                "entity_version": "1",
            }

            entity_data = {"message": "test content"}

            result = await repository.save(meta_with_type, entity_data)

            assert result == "msg-new-123"
            # Verify the request was made with correct path
            call_args = mock_request.call_args
            assert "message/new/TestMessage_1" in str(call_args)

    # Transition Tests

    @pytest.mark.asyncio
    async def test_launch_transition_success(self, repository, sample_meta):
        """Test _launch_transition for an entity."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"status": "success"},
                "status": 200,
            }

            meta_with_transition = {**sample_meta, "transition": "approve"}

            result = await repository._launch_transition(
                meta_with_transition, "test-id-123"
            )

            assert result is not None
            # Verify the request was made
            assert mock_request.called

    @pytest.mark.asyncio
    async def test_update_with_transition_only(self, repository, sample_meta):
        """Test update with transition but no entity data."""
        with patch.object(
            repository, "_launch_transition", new_callable=AsyncMock
        ) as mock_transition:
            mock_transition.return_value = None

            meta_with_transition = {**sample_meta, "transition": "approve"}

            result = await repository.update(meta_with_transition, "test-id-123", None)

            assert result is None
            # Check that _launch_transition was called
            mock_transition.assert_called_once()
            # Check the call arguments (using kwargs)
            call_kwargs = mock_transition.call_args.kwargs
            assert call_kwargs["meta"] == meta_with_transition
            assert call_kwargs["technical_id"] == "test-id-123"

    # Send Search Request Tests

    @pytest.mark.asyncio
    async def test_send_search_request_success(self, repository, sample_meta):
        """Test _send_search_request with successful response."""
        with patch("common.utils.utils.send_request") as mock_request:
            mock_request.return_value = {
                "json": [{"name": "Test", "id": "id-1"}],
                "status": 200,
            }

            criteria = {"name": "Test"}
            result = await repository._send_search_request(sample_meta, criteria, None)

            assert result["status"] == 200
            assert len(result["json"]) == 1

    @pytest.mark.asyncio
    async def test_send_search_request_with_401_retry(self, repository, sample_meta):
        """Test _send_search_request with 401 retry."""
        with patch("common.utils.utils.send_request") as mock_request:
            # First call returns 401, second succeeds
            mock_request.side_effect = [
                {"json": {"error": "Unauthorized"}, "status": 401},
                {"json": [{"name": "Test"}], "status": 200},
            ]

            criteria = {"name": "Test"}
            result = await repository._send_search_request(sample_meta, criteria, None)

            assert result["status"] == 200
            assert mock_request.call_count == 2

    # Update Error Handling Tests

    @pytest.mark.asyncio
    async def test_update_non_200_status(self, repository, sample_meta):
        """Test update with non-200 status response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"error": "Update failed"},
                "status": 500,
            }

            result = await repository.update(
                sample_meta, "test-id", {"name": "Updated"}
            )

            # Should return None on non-200 status
            assert result is None

    @pytest.mark.asyncio
    async def test_update_non_dict_response(self, repository, sample_meta):
        """Test update with non-dict response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": "not a dict",
                "status": 200,
            }

            result = await repository.update(
                sample_meta, "test-id", {"name": "Updated"}
            )

            # Should return None for non-dict response
            assert result is None

    @pytest.mark.asyncio
    async def test_update_no_entity_ids(self, repository, sample_meta):
        """Test update with no entityIds in response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"status": "success"},
                "status": 200,
            }

            result = await repository.update(
                sample_meta, "test-id", {"name": "Updated"}
            )

            # Should return None when no entityIds
            assert result is None

    @pytest.mark.asyncio
    async def test_update_empty_entity_ids(self, repository, sample_meta):
        """Test update with empty entityIds list."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": []},
                "status": 200,
            }

            result = await repository.update(
                sample_meta, "test-id", {"name": "Updated"}
            )

            # Should return None for empty entityIds
            assert result is None

    @pytest.mark.asyncio
    async def test_update_none_entity_id(self, repository, sample_meta):
        """Test update with None in entityIds."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"entityIds": [None]},
                "status": 200,
            }

            result = await repository.update(
                sample_meta, "test-id", {"name": "Updated"}
            )

            # Should return None when entityId is None
            assert result is None

    # Find by Key Tests

    @pytest.mark.asyncio
    async def test_find_by_key_success(self, repository, sample_meta):
        """Test finding entity by key."""
        with patch.object(
            repository, "find_all_by_criteria", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = [{"name": "Test", "key": "test-key"}]

            result = await repository.find_by_key(sample_meta, "test-key")

            assert result is not None
            assert result["key"] == "test-key"
            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_key_not_found(self, repository, sample_meta):
        """Test finding entity by key when not found."""
        with patch.object(
            repository, "find_all_by_criteria", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = []

            result = await repository.find_by_key(sample_meta, "nonexistent-key")

            assert result is None

    @pytest.mark.asyncio
    async def test_find_by_key_with_condition_in_meta(self, repository, sample_meta):
        """Test finding entity by key with condition in meta."""
        meta_with_condition = {**sample_meta, "condition": {"custom": "criteria"}}

        with patch.object(
            repository, "find_all_by_criteria", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = [{"name": "Test"}]

            result = await repository.find_by_key(meta_with_condition, "test-key")

            assert result is not None
            # Should use condition from meta
            call_args = mock_find.call_args
            assert call_args[0][1] == {"custom": "criteria"}

    @pytest.mark.asyncio
    async def test_exists_by_key_true(self, repository, sample_meta):
        """Test exists_by_key when entity exists."""
        with patch.object(
            repository, "find_by_key", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = {"name": "Test"}

            result = await repository.exists_by_key(sample_meta, "test-key")

            assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_key_false(self, repository, sample_meta):
        """Test exists_by_key when entity doesn't exist."""
        with patch.object(
            repository, "find_by_key", new_callable=AsyncMock
        ) as mock_find:
            mock_find.return_value = None

            result = await repository.exists_by_key(sample_meta, "test-key")

            assert result is False

    # Get Entity Count Tests

    @pytest.mark.asyncio
    async def test_get_entity_count_dict_response(self, repository, sample_meta):
        """Test get_entity_count with dict response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"count": 42},
                "status": 200,
            }

            result = await repository.get_entity_count(sample_meta)

            assert result == 42

    @pytest.mark.asyncio
    async def test_get_entity_count_list_response(self, repository, sample_meta):
        """Test get_entity_count with list response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"count": 10}, {"count": 20}, {"count": 15}],
                "status": 200,
            }

            result = await repository.get_entity_count(sample_meta)

            # Should sum all counts
            assert result == 45

    @pytest.mark.asyncio
    async def test_get_entity_count_non_200_status(self, repository, sample_meta):
        """Test get_entity_count with non-200 status."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"error": "Failed"},
                "status": 500,
            }

            result = await repository.get_entity_count(sample_meta)

            # Should return 0 on error
            assert result == 0

    @pytest.mark.asyncio
    async def test_get_entity_count_invalid_response(self, repository, sample_meta):
        """Test get_entity_count with invalid response format."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": "not a dict or list",
                "status": 200,
            }

            result = await repository.get_entity_count(sample_meta)

            # Should return 0 for invalid format
            assert result == 0

    # Get Entity Changes Metadata Tests

    @pytest.mark.asyncio
    async def test_get_entity_changes_metadata_success(self, repository):
        """Test get_entity_changes_metadata with successful response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [
                    {"timestamp": "2024-01-01", "change": "created"},
                    {"timestamp": "2024-01-02", "change": "updated"},
                ],
                "status": 200,
            }

            result = await repository.get_entity_changes_metadata("test-id")

            assert len(result) == 2
            assert result[0]["change"] == "created"
            assert result[1]["change"] == "updated"

    @pytest.mark.asyncio
    async def test_get_entity_changes_metadata_with_point_in_time(self, repository):
        """Test get_entity_changes_metadata with point_in_time."""
        from datetime import datetime

        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": [{"timestamp": "2024-01-01", "change": "created"}],
                "status": 200,
            }

            pit = datetime(2024, 1, 1, 12, 0, 0)
            result = await repository.get_entity_changes_metadata("test-id", pit)

            assert len(result) == 1
            # Verify point_in_time was added to path
            call_args = mock_request.call_args
            assert "pointInTime" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_entity_changes_metadata_non_200_status(self, repository):
        """Test get_entity_changes_metadata with non-200 status."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"error": "Failed"},
                "status": 500,
            }

            result = await repository.get_entity_changes_metadata("test-id")

            # Should return empty list on error
            assert result == []

    @pytest.mark.asyncio
    async def test_get_entity_changes_metadata_non_list_response(self, repository):
        """Test get_entity_changes_metadata with non-list response."""
        with patch(
            "common.repository.cyoda.cyoda_repository.send_cyoda_request"
        ) as mock_request:
            mock_request.return_value = {
                "json": {"changes": "not a list"},
                "status": 200,
            }

            result = await repository.get_entity_changes_metadata("test-id")

            # Should return empty list for non-list response
            assert result == []
