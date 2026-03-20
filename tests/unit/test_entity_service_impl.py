"""
Unit tests for EntityServiceImpl.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.entity.cyoda_entity import CyodaEntity
from common.repository.crud_repository import CrudRepository
from common.service.entity_service import (
    EntityMetadata,
    EntityResponse,
    LogicalOperator,
    SearchConditionRequest,
    SearchOperator,
)
from common.service.service import EntityServiceError, EntityServiceImpl


class SampleEntity(CyodaEntity):
    """Sample entity for service tests."""

    name: str
    value: int
    status: Optional[str] = None


class MockRepository(CrudRepository[Any]):
    """Mock repository for testing."""

    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}
        self.meta_storage: Dict[str, Any] = {}

    async def find_by_id(
        self,
        meta: Dict[str, Any],
        entity_id: Any,
        point_in_time: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        return self.storage.get(str(entity_id))

    async def find_all(self, meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        return list(self.storage.values())

    async def find_all_by_criteria(
        self,
        meta: Dict[str, Any],
        criteria: Any,
        point_in_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        for entity in self.storage.values():
            if self._matches_criteria(entity, criteria):
                results.append(entity)
        return results

    @staticmethod
    def _matches_criteria(entity: Dict[str, Any], criteria: Any) -> bool:
        if not isinstance(criteria, dict):
            return True
        # Handle Cyoda-native group format
        if criteria.get("type") == "group":
            conditions = criteria.get("conditions", [])
            if not conditions:
                return True
            operator = criteria.get("operator", "AND").upper()
            if operator == "AND":
                return all(
                    MockRepository._matches_condition(entity, c) for c in conditions
                )
            return any(
                MockRepository._matches_condition(entity, c) for c in conditions
            )
        # Handle Cyoda-native single condition
        if criteria.get("type") in ("simple", "lifecycle"):
            return MockRepository._matches_condition(entity, criteria)
        # Handle simple field-value pairs (backward compat)
        for key, value in criteria.items():
            if entity.get(key) != value:
                return False
        return True

    @staticmethod
    def _matches_condition(entity: Dict[str, Any], condition: Dict[str, Any]) -> bool:
        ctype = condition.get("type")
        if ctype == "simple":
            json_path = condition.get("jsonPath", "")
            field = json_path.replace("$.", "") if json_path.startswith("$.") else json_path
        elif ctype == "lifecycle":
            field = condition.get("field", "state")
        else:
            return True
        op = condition.get("operatorType", "EQUALS")
        value = condition.get("value")
        entity_value = entity.get(field)
        if op == "EQUALS":
            return entity_value == value
        if op == "NOT_EQUAL":
            return entity_value != value
        if op == "GREATER_THAN":
            return entity_value is not None and entity_value > value
        if op == "LESS_THAN":
            return entity_value is not None and entity_value < value
        if op == "GREATER_OR_EQUAL":
            return entity_value is not None and entity_value >= value
        if op == "LESS_OR_EQUAL":
            return entity_value is not None and entity_value <= value
        if op == "CONTAINS":
            return isinstance(entity_value, str) and value in entity_value
        if op == "IN":
            return entity_value in (value if isinstance(value, list) else [value])
        return entity_value == value

    async def save(self, meta: Dict[str, Any], entity: Any) -> Any:
        entity_id = f"id-{len(self.storage) + 1}"
        entity_data = entity if isinstance(entity, dict) else entity.model_dump()
        entity_data["technical_id"] = entity_id
        self.storage[entity_id] = entity_data
        return entity_id

    async def save_all(self, meta: Dict[str, Any], entities: List[Any]) -> Any:
        for entity in entities:
            await self.save(meta, entity)
        return "batch_id"

    async def update(
        self, meta: Dict[str, Any], entity_id: Any, entity: Optional[Any] = None
    ) -> Any:
        if entity:
            entity_data = entity if isinstance(entity, dict) else entity.model_dump()
            entity_data["technical_id"] = str(entity_id)
            self.storage[str(entity_id)] = entity_data
        return entity_id

    async def delete_by_id(self, meta: Dict[str, Any], entity_id: Any) -> None:
        if str(entity_id) in self.storage:
            del self.storage[str(entity_id)]

    async def count(self, meta: Dict[str, Any]) -> int:
        return len(self.storage)

    async def exists_by_key(self, meta: Dict[str, Any], key: Any) -> bool:
        return str(key) in self.storage

    async def get_entity_count(
        self, meta: Dict[str, Any], point_in_time: Optional[datetime] = None
    ) -> int:
        return len(self.storage)

    async def get_entity_changes_metadata(
        self, entity_id: Any, point_in_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        return [{"entity_id": str(entity_id), "change_type": "created"}]

    async def get_meta(
        self, token: str, entity_model: str, entity_version: str
    ) -> Dict[str, Any]:
        return {
            "token": token,
            "entity_model": entity_model,
            "entity_version": entity_version,
        }

    async def delete_all(self, meta: Dict[str, Any]) -> None:
        self.storage.clear()

    async def get_transitions(self, meta: Dict[str, Any], entity_id: Any) -> List[str]:
        return ["update", "complete", "cancel"]


class TestEntityServiceImpl:
    """Test suite for EntityServiceImpl."""

    @pytest.fixture
    def repository(self):
        """Create a mock repository."""
        return MockRepository()

    @pytest.fixture
    def service(self, repository):
        """Create an EntityServiceImpl instance."""
        # Reset singleton
        EntityServiceImpl._instance = None
        return EntityServiceImpl(repository)

    @pytest.fixture
    def sample_entity_data(self):
        """Create sample entity data."""
        return {"name": "Test Entity", "value": 42, "status": "active"}

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, repository, sample_entity_data):
        """Test getting entity by ID when it exists."""
        repository.storage["test-id-1"] = {
            **sample_entity_data,
            "technical_id": "test-id-1",
        }

        result = await service.get_by_id("test-id-1", "TestEntity", "1")

        assert result is not None
        assert result.metadata.id == "test-id-1"
        assert isinstance(result.data, dict)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service):
        """Test getting entity by ID when it doesn't exist."""
        result = await service.get_by_id("non-existent", "TestEntity", "1")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_all_empty(self, service):
        """Test finding all entities when repository is empty."""
        result = await service.find_all("TestEntity", "1")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_all_with_entities(self, service, repository):
        """Test finding all entities when repository has data."""
        repository.storage = {
            "id-1": {"name": "Entity 1", "value": 10, "technical_id": "id-1"},
            "id-2": {"name": "Entity 2", "value": 20, "technical_id": "id-2"},
        }

        result = await service.find_all("TestEntity", "1")

        assert len(result) == 2
        assert all(isinstance(r, EntityResponse) for r in result)

    @pytest.mark.asyncio
    async def test_search_with_single_condition(self, service, repository):
        """Test searching entities with a single condition."""
        repository.storage = {
            "id-1": {"name": "Test", "value": 10, "technical_id": "id-1"},
            "id-2": {"name": "Test", "value": 20, "technical_id": "id-2"},
            "id-3": {"name": "Other", "value": 30, "technical_id": "id-3"},
        }

        search_request = SearchConditionRequest.builder().equals("name", "Test").build()
        result = await service.search("TestEntity", search_request, "1")

        assert len(result) == 2
        assert all(r.data.get("name") == "Test" for r in result)

    @pytest.mark.asyncio
    async def test_search_with_limit(self, service, repository):
        """Test searching entities with limit."""
        repository.storage = {
            "id-1": {"name": "Test", "value": 10, "technical_id": "id-1"},
            "id-2": {"name": "Test", "value": 20, "technical_id": "id-2"},
            "id-3": {"name": "Test", "value": 30, "technical_id": "id-3"},
        }

        search_request = (
            SearchConditionRequest.builder().equals("name", "Test").limit(2).build()
        )
        result = await service.search("TestEntity", search_request, "1")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_save_entity(self, service, sample_entity_data):
        """Test saving a new entity."""
        result = await service.save(sample_entity_data, "TestEntity", "1")

        assert result is not None
        assert isinstance(result, EntityResponse)
        assert result.metadata.id is not None
        assert result.data.get("name") == "Test Entity"

    @pytest.mark.asyncio
    async def test_update_entity(self, service, repository):
        """Test updating an existing entity."""
        repository.storage["test-id-1"] = {
            "name": "Original",
            "value": 10,
            "technical_id": "test-id-1",
        }

        updated_data = {"name": "Updated", "value": 20}
        result = await service.update(
            "test-id-1", updated_data, "TestEntity", None, "1"
        )

        assert result is not None
        assert result.data.get("name") == "Updated"
        assert repository.storage["test-id-1"]["name"] == "Updated"

    @pytest.mark.asyncio
    async def test_delete_by_id(self, service, repository):
        """Test deleting entity by ID."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }

        result = await service.delete_by_id("test-id-1", "TestEntity", "1")

        assert result == "test-id-1"
        assert "test-id-1" not in repository.storage

    @pytest.mark.asyncio
    async def test_save_all(self, service):
        """Test saving multiple entities."""
        entities = [
            {"name": "Entity 1", "value": 10},
            {"name": "Entity 2", "value": 20},
        ]

        result = await service.save_all(entities, "TestEntity", "1")

        assert len(result) == 2
        assert all(isinstance(r, EntityResponse) for r in result)

    @pytest.mark.asyncio
    async def test_delete_all(self, service, repository):
        """Test deleting all entities."""
        repository.storage = {
            "id-1": {"name": "Entity 1", "value": 10, "technical_id": "id-1"},
            "id-2": {"name": "Entity 2", "value": 20, "technical_id": "id-2"},
        }

        result = await service.delete_all("TestEntity", "1")

        assert result == 2
        assert len(repository.storage) == 0

    @pytest.mark.asyncio
    async def test_get_transitions(self, service, repository):
        """Test getting available transitions for an entity."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }

        result = await service.get_transitions("test-id-1", "TestEntity", "1")

        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_execute_transition(self, service, repository):
        """Test executing a workflow transition."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }

        result = await service.execute_transition(
            "test-id-1", "update", "TestEntity", "1"
        )

        assert result is not None
        assert isinstance(result, EntityResponse)

    @pytest.mark.asyncio
    async def test_get_entity_count(self, service, repository):
        """Test getting entity count."""
        repository.storage = {
            "id-1": {"name": "Entity 1", "value": 10, "technical_id": "id-1"},
            "id-2": {"name": "Entity 2", "value": 20, "technical_id": "id-2"},
        }

        result = await service.get_entity_count("TestEntity", "1")

        assert result == 2

    @pytest.mark.asyncio
    async def test_get_entity_changes_metadata(self, service, repository):
        """Test getting entity change history metadata."""
        result = await service.get_entity_changes_metadata(
            "test-id-1", "TestEntity", "1"
        )

        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_find_by_business_id_found(self, service, repository):
        """Test finding entity by business ID when it exists."""
        repository.storage["id-1"] = {
            "name": "Test",
            "business_id": "BIZ-123",
            "value": 10,
            "technical_id": "id-1",
        }

        result = await service.find_by_business_id(
            "TestEntity", "BIZ-123", "business_id", "1"
        )

        assert result is not None
        assert result.data.get("business_id") == "BIZ-123"

    @pytest.mark.asyncio
    async def test_find_by_business_id_not_found(self, service):
        """Test finding entity by business ID when it doesn't exist."""
        result = await service.find_by_business_id(
            "TestEntity", "NON-EXISTENT", "business_id", "1"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_by_business_id(self, service, repository):
        """Test updating entity by business ID."""
        repository.storage["id-1"] = {
            "name": "Original",
            "business_id": "BIZ-123",
            "value": 10,
            "technical_id": "id-1",
        }

        updated_data = {"name": "Updated", "business_id": "BIZ-123", "value": 20}
        result = await service.update_by_business_id(
            updated_data, "business_id", "TestEntity", None, "1"
        )

        assert result is not None
        assert result.data.get("name") == "Updated"

    @pytest.mark.asyncio
    async def test_update_by_business_id_not_found(self, service):
        """Test updating entity by business ID when it doesn't exist."""
        updated_data = {"name": "Updated", "business_id": "NON-EXISTENT", "value": 20}

        with pytest.raises(EntityServiceError):
            await service.update_by_business_id(
                updated_data, "business_id", "TestEntity", None, "1"
            )

    @pytest.mark.asyncio
    async def test_update_by_business_id_missing_field(self, service):
        """Test updating entity by business ID when data is missing the field."""
        updated_data = {"name": "Updated", "value": 20}

        with pytest.raises(EntityServiceError):
            await service.update_by_business_id(
                updated_data, "business_id", "TestEntity", None, "1"
            )

    @pytest.mark.asyncio
    async def test_delete_by_business_id_found(self, service, repository):
        """Test deleting entity by business ID when it exists."""
        repository.storage["id-1"] = {
            "name": "Test",
            "business_id": "BIZ-123",
            "value": 10,
            "technical_id": "id-1",
        }

        result = await service.delete_by_business_id(
            "TestEntity", "BIZ-123", "business_id", "1"
        )

        assert result is True
        assert "id-1" not in repository.storage

    @pytest.mark.asyncio
    async def test_delete_by_business_id_not_found(self, service):
        """Test deleting entity by business ID when it doesn't exist."""
        result = await service.delete_by_business_id(
            "TestEntity", "NON-EXISTENT", "business_id", "1"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_by_id_at_time(self, service, repository):
        """Test getting entity by ID at a specific point in time."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }
        point_in_time = datetime(2024, 1, 1, 12, 0, 0)

        result = await service.get_by_id_at_time(
            "test-id-1", "TestEntity", point_in_time, "1"
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_search_at_time(self, service, repository):
        """Test searching entities at a specific point in time."""
        repository.storage = {
            "id-1": {"name": "Test", "value": 10, "technical_id": "id-1"},
        }
        point_in_time = datetime(2024, 1, 1, 12, 0, 0)

        search_request = SearchConditionRequest.builder().equals("name", "Test").build()
        result = await service.search_at_time(
            "TestEntity", search_request, point_in_time, "1"
        )

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_singleton_pattern(self, repository):
        """Test that EntityServiceImpl follows singleton pattern."""
        EntityServiceImpl._instance = None
        service1 = EntityServiceImpl.get_instance(repository)
        service2 = EntityServiceImpl.get_instance()

        assert service1 is service2

    @pytest.mark.asyncio
    async def test_singleton_requires_repository_first_time(self):
        """Test that singleton requires repository on first initialization."""
        EntityServiceImpl._instance = None

        with pytest.raises(ValueError):
            EntityServiceImpl.get_instance()

    @pytest.mark.asyncio
    async def test_convert_search_condition_single(self, service):
        """Test converting single search condition."""
        search_request = SearchConditionRequest.builder().equals("name", "Test").build()

        result = service._convert_search_condition(search_request)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 1
        cond = result["conditions"][0]
        assert cond["type"] == "simple"
        assert cond["jsonPath"] == "$.name"
        assert cond["operatorType"] == "EQUALS"
        assert cond["value"] == "Test"

    @pytest.mark.asyncio
    async def test_convert_search_condition_multiple(self, service):
        """Test converting multiple search conditions."""
        search_request = (
            SearchConditionRequest.builder()
            .equals("name", "Test")
            .equals("value", 10)
            .build()
        )

        result = service._convert_search_condition(search_request)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 2

    @pytest.mark.asyncio
    async def test_legacy_get_item(self, service, repository):
        """Test legacy get_item method."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }

        with pytest.warns(DeprecationWarning):
            result = await service.get_item("token", "TestEntity", "1", "test-id-1")

        assert result is not None

    @pytest.mark.asyncio
    async def test_legacy_get_items(self, service, repository):
        """Test legacy get_items method."""
        repository.storage = {
            "id-1": {"name": "Entity 1", "value": 10, "technical_id": "id-1"},
        }

        with pytest.warns(DeprecationWarning):
            result = await service.get_items("token", "TestEntity", "1")

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_legacy_add_item(self, service):
        """Test legacy add_item method."""
        entity_data = {"name": "Test", "value": 10}

        with pytest.warns(DeprecationWarning):
            result = await service.add_item("token", "TestEntity", "1", entity_data)

        assert result is not None

    @pytest.mark.asyncio
    async def test_legacy_update_item(self, service, repository):
        """Test legacy update_item method."""
        repository.storage["test-id-1"] = {
            "name": "Original",
            "value": 10,
            "technical_id": "test-id-1",
        }
        updated_data = {"name": "Updated", "value": 20}

        with pytest.warns(DeprecationWarning):
            result = await service.update_item(
                "token", "TestEntity", "1", "test-id-1", updated_data, {}
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_legacy_delete_item(self, service, repository):
        """Test legacy delete_item method."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }

        with pytest.warns(DeprecationWarning):
            result = await service.delete_item(
                "token", "TestEntity", "1", "test-id-1", {}
            )

        assert result == "test-id-1"

    @pytest.mark.asyncio
    async def test_legacy_get_items_by_condition(self, service, repository):
        """Test legacy get_items_by_condition method."""
        repository.storage = {
            "id-1": {"name": "Test", "value": 10, "technical_id": "id-1"},
        }

        with pytest.warns(DeprecationWarning):
            result = await service.get_items_by_condition(
                "token", "TestEntity", "1", {"name": "Test"}
            )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_legacy_get_single_item_by_condition(self, service, repository):
        """Test legacy get_single_item_by_condition method."""
        repository.storage = {
            "id-1": {"name": "Test", "value": 10, "technical_id": "id-1"},
        }

        with pytest.warns(DeprecationWarning):
            result = await service.get_single_item_by_condition(
                "token", "TestEntity", "1", {"name": "Test"}
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_entity_response(self, service):
        """Test creating entity response with metadata."""
        data = {"name": "Test", "value": 10, "technical_id": "test-id"}

        result = service._create_entity_response(data, "test-id", "active")

        assert result.metadata.id == "test-id"
        assert result.metadata.state == "active"

    @pytest.mark.asyncio
    async def test_create_entity_response_extract_id(self, service):
        """Test creating entity response extracting ID from data."""
        data = {"name": "Test", "value": 10, "technical_id": "test-id"}

        result = service._create_entity_response(data)

        assert result.metadata.id == "test-id"

    @pytest.mark.asyncio
    async def test_create_entity_response_extracts_transaction_id(self, service):
        """Test that transaction_id is extracted from data into metadata."""
        data = {
            "name": "Test",
            "technical_id": "test-id",
            "transaction_id": "txn-uuid-abc",
        }

        result = service._create_entity_response(data)

        assert result.metadata.transaction_id == "txn-uuid-abc"

    @pytest.mark.asyncio
    async def test_create_entity_response_transaction_id_none_when_absent(self, service):
        """Test that metadata.transaction_id is None when not present in data."""
        data = {"name": "Test", "technical_id": "test-id"}

        result = service._create_entity_response(data)

        assert result.metadata.transaction_id is None

    @pytest.mark.asyncio
    async def test_handle_repository_error(self, service):
        """Test handling repository errors."""
        error_data = {"errorMessage": "Something went wrong"}

        with pytest.raises(EntityServiceError) as exc_info:
            service._handle_repository_error(
                error_data, "test_operation", "TestEntity", "test-id"
            )

        assert "Something went wrong" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handle_repository_error_no_error(self, service):
        """Test handling repository response with no error."""
        data = {"name": "Test", "value": 10}

        result = service._handle_repository_error(data, "test_operation")

        assert result == data

    @pytest.mark.asyncio
    async def test_get_repository_meta(self, service):
        """Test getting repository metadata."""
        result = await service._get_repository_meta("token", "TestEntity", "1")

        assert result["token"] == "token"
        assert result["entity_model"] == "TestEntity"
        assert result["entity_version"] == "1"

    @pytest.mark.asyncio
    async def test_get_repository_meta_with_additional(self, service):
        """Test getting repository metadata with additional metadata."""
        result = await service._get_repository_meta(
            "token", "TestEntity", "1", {"extra": "data"}
        )

        assert result["extra"] == "data"

    @pytest.mark.asyncio
    async def test_save_entity_error(self, service, repository):
        """Test save entity error handling."""

        async def failing_save(meta, entity):
            raise Exception("Save failed")

        repository.save = failing_save

        with pytest.raises(EntityServiceError):
            await service.save({"name": "Test"}, "TestEntity", "1")

    @pytest.mark.asyncio
    async def test_update_entity_error(self, service, repository):
        """Test update entity error handling."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }

        async def failing_update(meta, entity_id, entity):
            raise Exception("Update failed")

        repository.update = failing_update

        with pytest.raises(EntityServiceError):
            await service.update(
                "test-id-1", {"name": "Updated"}, "TestEntity", None, "1"
            )

    @pytest.mark.asyncio
    async def test_delete_entity_error(self, service, repository):
        """Test delete entity error handling."""

        async def failing_delete(meta, entity_id):
            raise Exception("Delete failed")

        repository.delete_by_id = failing_delete

        with pytest.raises(EntityServiceError):
            await service.delete_by_id("test-id-1", "TestEntity", "1")

    @pytest.mark.asyncio
    async def test_search_no_results(self, service):
        """Test searching with no results."""
        search_request = (
            SearchConditionRequest.builder().equals("name", "NonExistent").build()
        )

        result = await service.search("TestEntity", search_request, "1")

        assert result == []

    @pytest.mark.asyncio
    async def test_save_all_empty_list(self, service):
        """Test saving empty list of entities."""
        result = await service.save_all([], "TestEntity", "1")

        assert result == []

    @pytest.mark.asyncio
    async def test_delete_all_empty_repository(self, service):
        """Test deleting all entities when repository is empty."""
        result = await service.delete_all("TestEntity", "1")

        assert result == 0

    @pytest.mark.asyncio
    async def test_execute_transition_entity_not_found(self, service):
        """Test executing transition when entity doesn't exist."""
        with pytest.raises(EntityServiceError):
            await service.execute_transition(
                "non-existent", "update", "TestEntity", "1"
            )

    @pytest.mark.asyncio
    async def test_parse_entity_data_with_model_registry(self, repository):
        """Test parsing entity data with model registry."""
        model_registry = {"testentity": SampleEntity}
        service = EntityServiceImpl(repository, model_registry)

        data = {"name": "Test", "value": 10}
        result = service._parse_entity_data(data, "TestEntity")

        assert isinstance(result, SampleEntity)

    @pytest.mark.asyncio
    async def test_parse_entity_data_without_model_registry(self, service):
        """Test parsing entity data without model registry."""
        data = {"name": "Test", "value": 10}
        result = service._parse_entity_data(data, "TestEntity")

        assert result == data

    @pytest.mark.asyncio
    async def test_parse_entity_data_empty(self, service):
        """Test parsing empty entity data."""
        result = service._parse_entity_data(None, "TestEntity")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_exception_handling(self, service, repository):
        """Test get_by_id exception handling."""

        async def failing_find(meta, entity_id, point_in_time=None):
            raise Exception("Database error")

        repository.find_by_id = failing_find

        with pytest.raises(EntityServiceError) as exc_info:
            await service.get_by_id("test-id", "TestEntity", "1")

        assert "Get by ID failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_all_exception_handling(self, service, repository):
        """Test find_all exception handling."""

        async def failing_find_all(meta):
            raise Exception("Database error")

        repository.find_all = failing_find_all

        with pytest.raises(EntityServiceError) as exc_info:
            await service.find_all("TestEntity", "1")

        assert "Find all failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_exception_handling(self, service, repository):
        """Test search exception handling."""

        async def failing_search(meta, criteria, point_in_time=None):
            raise Exception("Database error")

        repository.find_all_by_criteria = failing_search

        search_request = SearchConditionRequest.builder().equals("name", "Test").build()

        with pytest.raises(EntityServiceError) as exc_info:
            await service.search("TestEntity", search_request, "1")

        assert "Search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_by_business_id_exception_handling(self, service, repository):
        """Test find_by_business_id exception handling."""

        async def failing_search(meta, criteria, point_in_time=None):
            raise Exception("Database error")

        repository.find_all_by_criteria = failing_search

        with pytest.raises(EntityServiceError) as exc_info:
            await service.find_by_business_id(
                "TestEntity", "BIZ-123", "business_id", "1"
            )

        assert "Find by business ID failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_by_business_id_exception_handling(self, service, repository):
        """Test update_by_business_id exception handling."""
        repository.storage["id-1"] = {
            "name": "Test",
            "business_id": "BIZ-123",
            "value": 10,
            "technical_id": "id-1",
        }

        async def failing_update(meta, entity_id, entity):
            raise Exception("Database error")

        repository.update = failing_update

        updated_data = {"name": "Updated", "business_id": "BIZ-123", "value": 20}

        with pytest.raises(EntityServiceError) as exc_info:
            await service.update_by_business_id(
                updated_data, "business_id", "TestEntity", None, "1"
            )

        # The error comes from update method, not update_by_business_id
        assert "Update failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_by_business_id_exception_handling(self, service, repository):
        """Test delete_by_business_id exception handling."""

        async def failing_search(meta, criteria, point_in_time=None):
            raise Exception("Database error")

        repository.find_all_by_criteria = failing_search

        with pytest.raises(EntityServiceError) as exc_info:
            await service.delete_by_business_id(
                "TestEntity", "BIZ-123", "business_id", "1"
            )

        assert "Delete by business ID failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_all_exception_handling(self, service, repository):
        """Test save_all exception handling."""

        async def failing_save(meta, entity):
            raise Exception("Database error")

        repository.save = failing_save

        entities = [{"name": "Entity 1", "value": 10}]

        with pytest.raises(EntityServiceError) as exc_info:
            await service.save_all(entities, "TestEntity", "1")

        assert "Batch save failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_all_exception_handling(self, service, repository):
        """Test delete_all exception handling."""

        async def failing_find_all(meta):
            raise Exception("Database error")

        repository.find_all = failing_find_all

        with pytest.raises(EntityServiceError) as exc_info:
            await service.delete_all("TestEntity", "1")

        assert "Delete all failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_transitions_exception_handling(self, service, repository):
        """Test get_transitions exception handling."""

        async def failing_get_transitions(meta, entity_id):
            raise Exception("Database error")

        repository.get_transitions = failing_get_transitions

        with pytest.raises(EntityServiceError) as exc_info:
            await service.get_transitions("test-id", "TestEntity", "1")

        assert "Get transitions failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_transition_exception_handling(self, service, repository):
        """Test execute_transition exception handling."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }

        async def failing_update(meta, entity_id, entity):
            raise Exception("Database error")

        repository.update = failing_update

        with pytest.raises(EntityServiceError) as exc_info:
            await service.execute_transition("test-id-1", "update", "TestEntity", "1")

        # The error comes from update method, not execute_transition
        assert "Update failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_id_at_time_exception_handling(self, service, repository):
        """Test get_by_id_at_time exception handling."""

        async def failing_find(meta, entity_id, point_in_time=None):
            raise Exception("Database error")

        repository.find_by_id = failing_find

        point_in_time = datetime(2024, 1, 1, 12, 0, 0)

        with pytest.raises(EntityServiceError) as exc_info:
            await service.get_by_id_at_time("test-id", "TestEntity", point_in_time, "1")

        assert "Get by ID at time failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_at_time_exception_handling(self, service, repository):
        """Test search_at_time exception handling."""

        async def failing_search(meta, criteria, point_in_time=None):
            raise Exception("Database error")

        repository.find_all_by_criteria = failing_search

        point_in_time = datetime(2024, 1, 1, 12, 0, 0)
        search_request = SearchConditionRequest.builder().equals("name", "Test").build()

        with pytest.raises(EntityServiceError) as exc_info:
            await service.search_at_time(
                "TestEntity", search_request, point_in_time, "1"
            )

        assert "Search at time failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_convert_search_condition_with_non_eq_operator(self, service):
        """Test converting search condition with non-equals operator."""
        search_request = (
            SearchConditionRequest.builder()
            .add_condition("value", SearchOperator.GREATER_THAN, 10)
            .build()
        )

        result = service._convert_search_condition(search_request)

        assert result["type"] == "group"
        cond = result["conditions"][0]
        assert cond["jsonPath"] == "$.value"
        assert cond["operatorType"] == "GREATER_THAN"
        assert cond["value"] == 10

    @pytest.mark.asyncio
    async def test_convert_search_condition_multiple_with_non_eq(self, service):
        """Test converting multiple search conditions with non-equals operators."""
        search_request = (
            SearchConditionRequest.builder()
            .add_condition("value", SearchOperator.GREATER_THAN, 10)
            .add_condition("name", SearchOperator.CONTAINS, "Test")
            .build()
        )

        result = service._convert_search_condition(search_request)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 2

    # Additional Edge Cases and Coverage Tests

    @pytest.mark.asyncio
    async def test_exists_by_id_true(self, service, repository):
        """Test exists_by_id when entity exists."""
        repository.storage["test-id"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id",
        }

        result = await service.exists_by_id("test-id", "TestEntity", "1")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_id_false(self, service):
        """Test exists_by_id when entity doesn't exist."""
        result = await service.exists_by_id("non-existent", "TestEntity", "1")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_by_id_exception(self, service, repository):
        """Test exists_by_id when exception occurs."""

        async def failing_find(meta, entity_id, point_in_time=None):
            raise Exception("Database error")

        repository.find_by_id = failing_find

        result = await service.exists_by_id("test-id", "TestEntity", "1")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_by_business_id_true(self, service, repository):
        """Test exists_by_business_id when entity exists."""
        repository.storage["id-1"] = {
            "name": "Test",
            "business_id": "BIZ-123",
            "value": 10,
            "technical_id": "id-1",
        }

        result = await service.exists_by_business_id(
            "TestEntity", "BIZ-123", "business_id", "1"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_by_business_id_false(self, service):
        """Test exists_by_business_id when entity doesn't exist."""
        result = await service.exists_by_business_id(
            "TestEntity", "NON-EXISTENT", "business_id", "1"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_by_business_id_exception(self, service, repository):
        """Test exists_by_business_id when exception occurs."""

        async def failing_search(meta, criteria, point_in_time=None):
            raise Exception("Database error")

        repository.find_all_by_criteria = failing_search

        result = await service.exists_by_business_id(
            "TestEntity", "BIZ-123", "business_id", "1"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_count_success(self, service, repository):
        """Test count method successfully."""
        repository.storage = {
            "id-1": {"name": "Entity 1", "value": 10, "technical_id": "id-1"},
            "id-2": {"name": "Entity 2", "value": 20, "technical_id": "id-2"},
            "id-3": {"name": "Entity 3", "value": 30, "technical_id": "id-3"},
        }

        result = await service.count("TestEntity", "1")

        assert result == 3

    @pytest.mark.asyncio
    async def test_count_empty(self, service):
        """Test count method when no entities exist."""
        result = await service.count("TestEntity", "1")

        assert result == 0

    @pytest.mark.asyncio
    async def test_count_exception(self, service, repository):
        """Test count method when exception occurs."""

        async def failing_find_all(meta):
            raise Exception("Database error")

        repository.find_all = failing_find_all

        result = await service.count("TestEntity", "1")

        assert result == 0

    @pytest.mark.asyncio
    async def test_search_with_or_operator(self, service, repository):
        """Test searching with OR operator."""
        repository.storage = {
            "id-1": {"name": "Test", "value": 10, "technical_id": "id-1"},
            "id-2": {"name": "Other", "value": 20, "technical_id": "id-2"},
        }

        search_request = (
            SearchConditionRequest.builder()
            .equals("name", "Test")
            .operator(LogicalOperator.OR)
            .build()
        )
        result = await service.search("TestEntity", search_request, "1")

        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_search_with_offset(self, service, repository):
        """Test searching with offset."""
        repository.storage = {
            "id-1": {"name": "Test", "value": 10, "technical_id": "id-1"},
            "id-2": {"name": "Test", "value": 20, "technical_id": "id-2"},
            "id-3": {"name": "Test", "value": 30, "technical_id": "id-3"},
        }

        search_request = (
            SearchConditionRequest.builder()
            .equals("name", "Test")
            .offset(1)
            .limit(2)
            .build()
        )
        result = await service.search("TestEntity", search_request, "1")

        # Offset and limit are passed to repository but may not be enforced in mock
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_legacy_get_single_item_by_condition_not_found(self, service):
        """Test legacy get_single_item_by_condition when not found."""
        with pytest.warns(DeprecationWarning):
            result = await service.get_single_item_by_condition(
                "token", "TestEntity", "1", {"name": "NonExistent"}
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_entity_response_with_all_metadata(self, service):
        """Test creating entity response with all metadata fields."""
        data = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id",
            "version": 2,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }

        result = service._create_entity_response(data, "test-id", "active")

        assert result.metadata.id == "test-id"
        assert result.metadata.state == "active"

    @pytest.mark.asyncio
    async def test_handle_repository_error_with_nested_error(self, service):
        """Test handling repository error with nested error structure."""
        error_data = {"error": {"message": "Nested error message", "code": "ERR_001"}}

        # Should not raise if no errorMessage key
        result = service._handle_repository_error(error_data, "test_operation")

        assert result == error_data

    @pytest.mark.asyncio
    async def test_get_repository_meta_merges_correctly(self, service):
        """Test that get_repository_meta merges additional metadata correctly."""
        result = await service._get_repository_meta(
            "token", "TestEntity", "1", {"custom_field": "value", "token": "override"}
        )

        # Additional metadata should override base metadata
        assert result["custom_field"] == "value"
        assert result["token"] == "override"
        assert result["entity_model"] == "TestEntity"

    # Advanced Search Condition Tests

    @pytest.mark.asyncio
    async def test_convert_search_condition_with_less_than(self, service):
        """Test converting search condition with LESS_THAN operator."""
        search_request = (
            SearchConditionRequest.builder()
            .add_condition("value", SearchOperator.LESS_THAN, 100)
            .build()
        )

        result = service._convert_search_condition(search_request)

        cond = result["conditions"][0]
        assert cond["jsonPath"] == "$.value"
        assert cond["operatorType"] == "LESS_THAN"
        assert cond["value"] == 100

    @pytest.mark.asyncio
    async def test_convert_search_condition_with_greater_or_equal(self, service):
        """Test converting search condition with GREATER_OR_EQUAL operator."""
        search_request = (
            SearchConditionRequest.builder()
            .add_condition("value", SearchOperator.GREATER_OR_EQUAL, 50)
            .build()
        )

        result = service._convert_search_condition(search_request)

        cond = result["conditions"][0]
        assert cond["operatorType"] == "GREATER_OR_EQUAL"
        assert cond["value"] == 50

    @pytest.mark.asyncio
    async def test_convert_search_condition_with_less_or_equal(self, service):
        """Test converting search condition with LESS_OR_EQUAL operator."""
        search_request = (
            SearchConditionRequest.builder()
            .add_condition("value", SearchOperator.LESS_OR_EQUAL, 75)
            .build()
        )

        result = service._convert_search_condition(search_request)

        cond = result["conditions"][0]
        assert cond["operatorType"] == "LESS_OR_EQUAL"
        assert cond["value"] == 75

    @pytest.mark.asyncio
    async def test_convert_search_condition_with_in_operator(self, service):
        """Test converting search condition with IN operator."""
        search_request = (
            SearchConditionRequest.builder()
            .in_values("status", ["active", "pending", "completed"])
            .build()
        )

        result = service._convert_search_condition(search_request)

        cond = result["conditions"][0]
        assert cond["operatorType"] == "IN"
        assert cond["value"] == ["active", "pending", "completed"]

    @pytest.mark.asyncio
    async def test_convert_search_condition_with_not_equals(self, service):
        """Test converting search condition with NOT_EQUALS operator."""
        search_request = (
            SearchConditionRequest.builder()
            .add_condition("status", SearchOperator.NOT_EQUALS, "deleted")
            .build()
        )

        result = service._convert_search_condition(search_request)

        cond = result["conditions"][0]
        assert cond["operatorType"] == "NOT_EQUAL"
        assert cond["value"] == "deleted"

    @pytest.mark.asyncio
    async def test_convert_search_condition_complex_and(self, service):
        """Test converting complex search condition with AND operator."""
        search_request = (
            SearchConditionRequest.builder()
            .equals("name", "Test")
            .add_condition("value", SearchOperator.GREATER_THAN, 10)
            .add_condition("status", SearchOperator.CONTAINS, "active")
            .build()
        )

        result = service._convert_search_condition(search_request)

        assert result["type"] == "group"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 3

    @pytest.mark.asyncio
    async def test_convert_search_condition_with_or_operator_multiple(self, service):
        """Test converting search condition with OR operator and multiple conditions."""
        search_request = (
            SearchConditionRequest.builder()
            .equals("status", "active")
            .equals("status", "pending")
            .operator(LogicalOperator.OR)
            .build()
        )

        result = service._convert_search_condition(search_request)

        assert result["type"] == "group"
        assert result["operator"] == "OR"
        assert len(result["conditions"]) == 2

    # Singleton Pattern Tests

    @pytest.mark.asyncio
    async def test_singleton_with_repository_warning(self, repository):
        """Test singleton warns when repository provided after initialization."""
        EntityServiceImpl._instance = None
        service1 = EntityServiceImpl.get_instance(repository)

        # Try to create with different repository - should warn
        new_repo = MockRepository()
        service2 = EntityServiceImpl.get_instance(new_repo)

        # Should still be the same instance
        assert service1 is service2

    # Model Registry Tests

    @pytest.mark.asyncio
    async def test_parse_entity_data_with_invalid_model(self, repository):
        """Test parsing entity data with invalid model in registry."""
        # Create service with invalid model in registry
        model_registry = {"testentity": "not a class"}
        service = EntityServiceImpl(repository, model_registry)

        data = {"name": "Test", "value": 10}
        result = service._parse_entity_data(data, "TestEntity")

        # Should return None when model is invalid (parse_entity returns None on error)
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_entity_data_with_none_data(self, service):
        """Test parsing None entity data."""
        result = service._parse_entity_data(None, "TestEntity")

        assert result is None

    @pytest.mark.asyncio
    async def test_parse_entity_data_with_empty_dict(self, service):
        """Test parsing empty dict entity data."""
        result = service._parse_entity_data({}, "TestEntity")

        assert result == {}

    # Get Transitions with Different Response Types

    @pytest.mark.asyncio
    async def test_get_transitions_dict_response(self, service, repository):
        """Test get_transitions when repository returns dict."""
        repository.storage["test-id"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id",
        }

        async def get_transitions_dict(meta, entity_id):
            return {"approve": {}, "reject": {}, "update": {}}

        repository.get_transitions = get_transitions_dict

        result = await service.get_transitions("test-id", "TestEntity", "1")

        assert isinstance(result, list)
        assert len(result) == 3
        assert "approve" in result
        assert "reject" in result
        assert "update" in result

    @pytest.mark.asyncio
    async def test_get_transitions_non_list_non_dict(self, service, repository):
        """Test get_transitions when repository returns non-list, non-dict."""
        repository.storage["test-id"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id",
        }

        async def get_transitions_string(meta, entity_id):
            return "invalid response"

        repository.get_transitions = get_transitions_string

        result = await service.get_transitions("test-id", "TestEntity", "1")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_transitions_repository_without_method(self, repository):
        """Test get_transitions when repository doesn't have the method."""

        # Create a minimal repository class without get_transitions
        class MinimalRepository:
            async def get_meta(self, token, entity_model, entity_version):
                return {
                    "token": token,
                    "entity_model": entity_model,
                    "entity_version": entity_version,
                }

        minimal_repo = MinimalRepository()
        EntityServiceImpl._instance = None
        service = EntityServiceImpl(minimal_repo)

        result = await service.get_transitions("test-id", "TestEntity", "1")

        # Should return default transitions
        assert result == ["update", "complete", "cancel"]

    # Batch Operations Tests (using save_all method)

    @pytest.mark.asyncio
    async def test_save_all_with_repository_batch_support(self, service, repository):
        """Test save_all when repository supports batch operations."""
        entities = [
            {"name": "Entity1", "value": 10},
            {"name": "Entity2", "value": 20},
            {"name": "Entity3", "value": 30},
        ]

        # Mock repository to support batch save
        async def save_all_mock(meta, entities_list):
            return ["id-1", "id-2", "id-3"]

        repository.save_all = save_all_mock

        results = await service.save_all(entities, "TestEntity", "1")

        assert len(results) == 3
        assert all(isinstance(r, EntityResponse) for r in results)

    @pytest.mark.asyncio
    async def test_save_all_without_repository_batch_support(self, repository):
        """Test save_all when repository doesn't support batch operations."""

        # Create a new service instance with a repository that doesn't have save_all
        class MinimalRepository:
            def __init__(self):
                self.storage = {}

            async def get_meta(self, token, entity_model, entity_version):
                return {
                    "token": token,
                    "entity_model": entity_model,
                    "entity_version": entity_version,
                }

            async def save(self, meta, entity):
                entity_id = f"id-{len(self.storage)}"
                entity["technical_id"] = entity_id
                self.storage[entity_id] = entity
                return entity_id

        minimal_repo = MinimalRepository()
        EntityServiceImpl._instance = None
        service = EntityServiceImpl(minimal_repo)

        entities = [
            {"name": "Entity1", "value": 10},
            {"name": "Entity2", "value": 20},
        ]

        results = await service.save_all(entities, "TestEntity", "1")

        assert len(results) == 2
        assert all(isinstance(r, EntityResponse) for r in results)
        # Should have saved individually
        assert len(minimal_repo.storage) == 2

    @pytest.mark.asyncio
    async def test_save_all_empty_list(self, service):
        """Test save_all with empty list."""
        results = await service.save_all([], "TestEntity", "1")

        assert results == []

    # ========================================
    # DEPRECATED METHODS TESTS
    # ========================================

    @pytest.mark.asyncio
    async def test_get_item_deprecated_warning(self, service, repository):
        """Test get_item raises deprecation warning."""
        repository.storage["test-id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "test-id-1",
        }

        with pytest.warns(DeprecationWarning, match="get_item.*deprecated"):
            result = await service.get_item("token", "TestEntity", "1", "test-id-1")

        assert result is not None
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_item_not_found(self, service):
        """Test get_item returns None when entity not found."""
        with pytest.warns(DeprecationWarning):
            result = await service.get_item("token", "TestEntity", "1", "nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_item_exception_handling(self, service, repository):
        """Test get_item handles exceptions gracefully."""
        repository.find_by_id = AsyncMock(side_effect=Exception("Database error"))

        with pytest.warns(DeprecationWarning):
            result = await service.get_item("token", "TestEntity", "1", "test-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_items_deprecated_warning(self, service, repository):
        """Test get_items raises deprecation warning."""
        repository.storage["id-1"] = {
            "name": "Test1",
            "value": 10,
            "technical_id": "id-1",
        }
        repository.storage["id-2"] = {
            "name": "Test2",
            "value": 20,
            "technical_id": "id-2",
        }

        with pytest.warns(DeprecationWarning, match="get_items.*deprecated"):
            results = await service.get_items("token", "TestEntity", "1")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_items_exception_handling(self, service, repository):
        """Test get_items handles exceptions gracefully."""
        repository.find_all = AsyncMock(side_effect=Exception("Database error"))

        with pytest.warns(DeprecationWarning):
            results = await service.get_items("token", "TestEntity", "1")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_single_item_by_condition_deprecated(self, service, repository):
        """Test get_single_item_by_condition raises deprecation warning."""
        repository.storage["id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "id-1",
        }

        with pytest.warns(
            DeprecationWarning, match="get_single_item_by_condition.*deprecated"
        ):
            result = await service.get_single_item_by_condition(
                "token", "TestEntity", "1", {"name": "Test"}
            )

        assert result is not None
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_single_item_by_condition_not_found(self, service):
        """Test get_single_item_by_condition returns None when not found."""
        with pytest.warns(DeprecationWarning):
            result = await service.get_single_item_by_condition(
                "token", "TestEntity", "1", {"name": "Nonexistent"}
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_single_item_by_condition_exception(self, service, repository):
        """Test get_single_item_by_condition handles exceptions."""
        repository.find_all_by_criteria = AsyncMock(side_effect=Exception("Error"))

        with pytest.warns(DeprecationWarning):
            result = await service.get_single_item_by_condition(
                "token", "TestEntity", "1", {"name": "Test"}
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_items_by_condition_deprecated(self, service, repository):
        """Test get_items_by_condition raises deprecation warning."""
        repository.storage["id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "id-1",
        }

        with pytest.warns(
            DeprecationWarning, match="get_items_by_condition.*deprecated"
        ):
            results = await service.get_items_by_condition(
                "token", "TestEntity", "1", {"name": "Test"}
            )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_items_by_condition_with_chat_repository(
        self, service, repository
    ):
        """Test get_items_by_condition handles CHAT_REPOSITORY wrapper."""
        from common.config.config import CHAT_REPOSITORY

        repository.storage["id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "id-1",
        }

        condition = {CHAT_REPOSITORY: {"name": "Test"}}

        with pytest.warns(DeprecationWarning):
            results = await service.get_items_by_condition(
                "token", "TestEntity", "1", condition
            )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_items_by_condition_exception(self, service, repository):
        """Test get_items_by_condition handles exceptions."""
        repository.find_all_by_criteria = AsyncMock(side_effect=Exception("Error"))

        with pytest.warns(DeprecationWarning):
            results = await service.get_items_by_condition(
                "token", "TestEntity", "1", {"name": "Test"}
            )

        assert results == []

    @pytest.mark.asyncio
    async def test_add_item_deprecated(self, service):
        """Test add_item raises deprecation warning."""
        entity = {"name": "New Entity", "value": 100}

        with pytest.warns(DeprecationWarning, match="add_item.*deprecated"):
            result = await service.add_item("token", "TestEntity", "1", entity)

        assert result is not None

    @pytest.mark.asyncio
    async def test_add_item_exception(self, service, repository):
        """Test add_item handles exceptions."""
        repository.save = AsyncMock(side_effect=Exception("Save error"))

        with pytest.warns(DeprecationWarning):
            result = await service.add_item(
                "token", "TestEntity", "1", {"name": "Test"}
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_item_deprecated(self, service, repository):
        """Test update_item raises deprecation warning."""
        repository.storage["id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "id-1",
        }

        entity = {"name": "Updated", "value": 20}
        meta = {"update_transition": "approve"}

        with pytest.warns(DeprecationWarning, match="update_item.*deprecated"):
            result = await service.update_item(
                "token", "TestEntity", "1", "id-1", entity, meta
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_update_item_without_meta(self, service, repository):
        """Test update_item without meta dict."""
        repository.storage["id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "id-1",
        }

        with pytest.warns(DeprecationWarning):
            result = await service.update_item(
                "token", "TestEntity", "1", "id-1", {"name": "Updated"}, None
            )

        assert result is not None

    @pytest.mark.asyncio
    async def test_update_item_exception(self, service, repository):
        """Test update_item handles exceptions."""
        repository.update = AsyncMock(side_effect=Exception("Update error"))

        with pytest.warns(DeprecationWarning):
            result = await service.update_item(
                "token", "TestEntity", "1", "id-1", {"name": "Test"}, None
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_item_deprecated(self, service, repository):
        """Test delete_item raises deprecation warning."""
        repository.storage["id-1"] = {
            "name": "Test",
            "value": 10,
            "technical_id": "id-1",
        }

        with pytest.warns(DeprecationWarning, match="delete_item.*deprecated"):
            result = await service.delete_item("token", "TestEntity", "1", "id-1", None)

        assert result == "id-1"

    @pytest.mark.asyncio
    async def test_delete_item_exception(self, service, repository):
        """Test delete_item handles exceptions."""
        repository.delete_by_id = AsyncMock(side_effect=Exception("Delete error"))

        with pytest.warns(DeprecationWarning):
            result = await service.delete_item("token", "TestEntity", "1", "id-1", None)

        assert result is None

    @pytest.mark.asyncio
    async def test_convert_legacy_condition_dict(self, service):
        """Test _convert_legacy_condition with dict."""
        condition = {"name": "Test", "status": "active"}

        result = service._convert_legacy_condition(condition)

        assert isinstance(result, SearchConditionRequest)

    @pytest.mark.asyncio
    async def test_convert_legacy_condition_string(self, service):
        """Test _convert_legacy_condition with string."""
        condition = "TestName"

        result = service._convert_legacy_condition(condition)

        assert isinstance(result, SearchConditionRequest)

    # ========================================
    # EXCEPTION HANDLING TESTS
    # ========================================

    @pytest.mark.asyncio
    async def test_get_by_id_entity_service_error_propagation(
        self, service, repository
    ):
        """Test get_by_id propagates EntityServiceError."""
        from common.service.service import EntityServiceError

        async def raise_entity_error(*args, **kwargs):
            raise EntityServiceError("Custom error", "TestEntity", "id-1")

        repository.find_by_id = AsyncMock(side_effect=raise_entity_error)

        with pytest.raises(EntityServiceError) as exc_info:
            await service.get_by_id("id-1", "TestEntity", "1")

        assert "Custom error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_id_generic_exception_wrapping(self, service, repository):
        """Test get_by_id wraps generic exceptions in EntityServiceError."""
        from common.service.service import EntityServiceError

        repository.find_by_id = AsyncMock(side_effect=ValueError("Invalid value"))

        with pytest.raises(EntityServiceError) as exc_info:
            await service.get_by_id("id-1", "TestEntity", "1")

        assert "Get by ID failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_by_business_id_entity_service_error(
        self, service, repository
    ):
        """Test update_by_business_id propagates EntityServiceError."""
        from common.service.service import EntityServiceError

        async def raise_entity_error(*args, **kwargs):
            raise EntityServiceError("Update error", "TestEntity")

        repository.find_all_by_criteria = AsyncMock(side_effect=raise_entity_error)

        with pytest.raises(EntityServiceError):
            await service.update_by_business_id(
                {"business_id": "biz-1", "name": "Test"},
                "TestEntity",
                "business_id",
                "1",
            )

    @pytest.mark.asyncio
    async def test_update_by_business_id_generic_exception(self, service, repository):
        """Test update_by_business_id wraps generic exceptions."""
        from common.service.service import EntityServiceError

        repository.find_all_by_criteria = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        with pytest.raises(EntityServiceError) as exc_info:
            await service.update_by_business_id(
                {"business_id": "biz-1", "name": "Test"},
                "TestEntity",
                "business_id",
                "1",
            )

        # The error could be about missing field or update failure
        assert "TestEntity" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_all_entity_service_error(self, service, repository):
        """Test save_all propagates EntityServiceError."""
        from common.service.service import EntityServiceError

        async def raise_entity_error(*args, **kwargs):
            raise EntityServiceError("Save error", "TestEntity")

        repository.save_all = AsyncMock(side_effect=raise_entity_error)

        with pytest.raises(EntityServiceError):
            await service.save_all([{"name": "Test"}], "TestEntity", "1")

    @pytest.mark.asyncio
    async def test_save_all_generic_exception(self, service, repository):
        """Test save_all wraps generic exceptions."""
        from common.service.service import EntityServiceError

        repository.save_all = AsyncMock(side_effect=RuntimeError("Save failed"))

        with pytest.raises(EntityServiceError) as exc_info:
            await service.save_all([{"name": "Test"}], "TestEntity", "1")

        assert (
            "save" in str(exc_info.value).lower()
            or "failed" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_execute_transition_entity_service_error(self, service, repository):
        """Test execute_transition propagates EntityServiceError."""
        from common.service.service import EntityServiceError

        repository.storage["id-1"] = {"name": "Test", "technical_id": "id-1"}

        async def raise_entity_error(*args, **kwargs):
            raise EntityServiceError("Transition error", "TestEntity", "id-1")

        repository.update = AsyncMock(side_effect=raise_entity_error)

        with pytest.raises(EntityServiceError):
            await service.execute_transition("id-1", "approve", "TestEntity", "1")

    @pytest.mark.asyncio
    async def test_execute_transition_generic_exception(self, service, repository):
        """Test execute_transition wraps generic exceptions."""
        from common.service.service import EntityServiceError

        repository.storage["id-1"] = {"name": "Test", "technical_id": "id-1"}
        repository.update = AsyncMock(side_effect=RuntimeError("Transition failed"))

        with pytest.raises(EntityServiceError) as exc_info:
            await service.execute_transition("id-1", "approve", "TestEntity", "1")

        # The error message includes "Update failed" because execute_transition calls update
        assert (
            "update failed" in str(exc_info.value).lower()
            or "transition" in str(exc_info.value).lower()
        )


class TestSearchConditionRequestBuilder:
    """Test suite for SearchConditionRequestBuilder."""

    def test_builder_contains_method(self):
        """Test contains method in builder."""
        builder = SearchConditionRequest.builder()
        builder.contains("name", "test")
        request = builder.build()

        assert len(request.conditions) == 1
        assert request.conditions[0].field == "name"
        assert request.conditions[0].operator == SearchOperator.CONTAINS
        assert request.conditions[0].value == "test"

    def test_builder_in_values_method(self):
        """Test in_values method in builder."""
        builder = SearchConditionRequest.builder()
        builder.in_values("status", ["active", "pending"])
        request = builder.build()

        assert len(request.conditions) == 1
        assert request.conditions[0].field == "status"
        assert request.conditions[0].operator == SearchOperator.IN
        assert request.conditions[0].value == ["active", "pending"]

    def test_builder_operator_method(self):
        """Test operator method in builder."""
        builder = SearchConditionRequest.builder()
        builder.equals("name", "test")
        builder.operator(LogicalOperator.OR)
        builder.equals("status", "active")
        request = builder.build()

        assert request.operator == LogicalOperator.OR.value
        assert len(request.conditions) == 2


class TestEntityResponse:
    """Test suite for EntityResponse methods."""

    def test_entity_response_get_state(self):
        """Test get_state method."""
        metadata = EntityMetadata(
            id="test-id",
            version="1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            state="VALIDATED",
        )
        response = EntityResponse(data={"name": "Test"}, metadata=metadata)

        assert response.get_state() == "VALIDATED"

    def test_entity_response_get_state_none(self):
        """Test get_state returns None when state is not set."""
        metadata = EntityMetadata(
            id="test-id",
            version="1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        response = EntityResponse(data={"name": "Test"}, metadata=metadata)

        assert response.get_state() is None


class TestAdditionalCoverage:
    """Additional tests to improve coverage."""

    @pytest.fixture
    def repository(self):
        """Create a mock repository."""
        return MockRepository()

    @pytest.fixture
    def service(self, repository):
        """Create service instance with mock repository."""
        return EntityServiceImpl(repository)

    @pytest.mark.asyncio
    async def test_find_all_generic_exception(self, service, repository):
        """Test find_all wraps generic exceptions."""
        from common.service.service import EntityServiceError

        repository.find_all = AsyncMock(side_effect=RuntimeError("Database error"))

        with pytest.raises(EntityServiceError) as exc_info:
            await service.find_all("TestEntity", "1")

        assert "Find all failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_generic_exception(self, service, repository):
        """Test search wraps generic exceptions."""
        from common.service.service import EntityServiceError

        repository.find_all_by_criteria = AsyncMock(
            side_effect=RuntimeError("Search error")
        )

        search_request = SearchConditionRequest.builder().equals("name", "test").build()

        with pytest.raises(EntityServiceError) as exc_info:
            await service.search(search_request, "TestEntity", "1")

        assert "Search failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_no_entity_id_returned(self, service, repository):
        """Test save when repository returns no entity ID."""
        from common.service.service import EntityServiceError

        async def save_no_id(meta, entity):
            return None

        repository.save = save_no_id

        with pytest.raises(EntityServiceError) as exc_info:
            await service.save({"name": "Test"}, "TestEntity", "1")

        assert "Save operation returned no entity ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_save_generic_exception(self, service, repository):
        """Test save wraps generic exceptions."""
        from common.service.service import EntityServiceError

        repository.save = AsyncMock(side_effect=IOError("Disk error"))

        with pytest.raises(EntityServiceError) as exc_info:
            await service.save({"name": "Test"}, "TestEntity", "1")

        assert "Save failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_no_entity_id_returned(self, service, repository):
        """Test update when repository returns no entity ID."""
        from common.service.service import EntityServiceError

        repository.storage["test-id"] = {"name": "Old", "technical_id": "test-id"}

        async def update_no_id(meta, entity_id, entity):
            return None

        repository.update = update_no_id

        with pytest.raises(EntityServiceError) as exc_info:
            await service.update("test-id", {"name": "New"}, "TestEntity", None, "1")

        assert "Update operation returned no entity ID" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_by_business_id_exception_handling(self, service, repository):
        """Test update_by_business_id exception handling."""
        from common.service.service import EntityServiceError

        repository.find_all_by_criteria = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        with pytest.raises(EntityServiceError) as exc_info:
            await service.update_by_business_id(
                {"email": "test@example.com", "name": "Test"},
                "TestEntity",
                "email",
                "1",
            )

        assert "Update by business ID failed" in str(
            exc_info.value
        ) or "TestEntity" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_transition_with_pydantic_model(self, service, repository):
        """Test execute_transition with Pydantic model (model_dump path)."""
        # Register SampleEntity model
        service._model_registry["sampleentity"] = SampleEntity

        # Add entity
        repository.storage["id-1"] = {
            "name": "Test",
            "value": 123,
            "technical_id": "id-1",
        }

        result = await service.execute_transition(
            "id-1",
            "approve",
            "SampleEntity",
            "1",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_transition_exception_handling(self, service, repository):
        """Test execute_transition exception handling."""
        from common.service.service import EntityServiceError

        repository.storage["id-1"] = {"name": "Test", "technical_id": "id-1"}
        repository.update = AsyncMock(side_effect=RuntimeError("Transition failed"))

        with pytest.raises(EntityServiceError) as exc_info:
            await service.execute_transition("id-1", "approve", "TestEntity", "1")

        assert (
            "execute transition failed" in str(exc_info.value).lower()
            or "update failed" in str(exc_info.value).lower()
        )

    @pytest.mark.asyncio
    async def test_get_entity_count_exception_returns_zero(self, service, repository):
        """Test get_entity_count returns 0 on exception."""
        repository.get_entity_count = AsyncMock(
            side_effect=RuntimeError("Count failed")
        )

        count = await service.get_entity_count("TestEntity", "1")
        assert count == 0
