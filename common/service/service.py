"""
Enhanced Entity Service Implementation

This module provides a comprehensive implementation of the EntityService interface
with proper error handling, type safety, and performance optimizations.
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from common.config.config import CHAT_REPOSITORY
from common.repository.crud_repository import CrudRepository
from common.service.entity_service import (
    EntityMetadata,
    EntityResponse,
    EntityService,
    SearchCondition,
    SearchConditionRequest,
)
from common.utils.utils import parse_entity

logger = logging.getLogger("quart")


class EntityServiceError(Exception):
    """Custom exception for entity service operations."""

    def __init__(
        self,
        message: str,
        entity_class: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.entity_class = entity_class
        self.entity_id = entity_id


class EntityServiceImpl(EntityService):
    """
    Enhanced implementation of EntityService with comprehensive functionality.

    Features:
    - Thread-safe singleton pattern
    - Comprehensive error handling
    - Type-safe operations
    - Performance optimizations
    - Full interface compliance
    """

    _instance: Optional["EntityServiceImpl"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(
        self,
        repository: CrudRepository[Any],
        model_registry: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize EntityService implementation.

        Args:
            repository: CRUD repository for data operations
            model_registry: Registry of entity model classes
        """
        self._repository: CrudRepository[Any] = repository
        self._model_registry: Dict[str, Any] = model_registry or {}
        logger.info("EntityServiceImpl initialized")

    @classmethod
    def get_instance(
        cls,
        repository: Optional[CrudRepository[Any]] = None,
        model_registry: Optional[Dict[str, Any]] = None,
    ) -> "EntityServiceImpl":
        """
        Get singleton instance of EntityServiceImpl.

        Args:
            repository: CRUD repository for data operations (required for first initialization)
            model_registry: Registry of entity model classes

        Returns:
            EntityServiceImpl instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if repository is None:
                        raise ValueError(
                            "Repository is required for first initialization"
                        )
                    # Create instance without calling __init__, then set fields safely
                    instance = super().__new__(cls)  # type: ignore[call-arg]
                    # Attach attributes directly to avoid calling __init__ on an existing instance
                    instance._repository = repository  # type: ignore[attr-defined]
                    instance._model_registry = model_registry or {}  # type: ignore[attr-defined]
                    logger.info("EntityServiceImpl singleton created")
                    cls._instance = instance  # type: ignore[assignment]
        elif repository is not None:
            # If instance exists but repository is provided, log a warning
            logger.warning(
                "EntityServiceImpl instance already exists. Ignoring provided repository."
            )

        return cls._instance  # type: ignore[return-value]

    # ========================================
    # HELPER METHODS
    # ========================================

    def _create_entity_response(
        self, data: Any, entity_id: Optional[str] = None, state: Optional[str] = None
    ) -> EntityResponse:
        """
        Create EntityResponse with proper metadata.

        Args:
            data: Entity data
            entity_id: Technical UUID
            state: Entity state

        Returns:
            EntityResponse with data and metadata
        """
        # Extract technical_id from data if not provided
        if entity_id is None and isinstance(data, dict):
            entity_id = data.get("technical_id") or data.get("id")

        # Extract state from data if not provided
        if state is None and isinstance(data, dict):
            state = data.get("current_state") or data.get("state")

        transaction_id = data.get("transaction_id") if isinstance(data, dict) else None

        metadata = EntityMetadata(
            id=entity_id or "unknown",
            state=state,
            created_at=datetime.now(),
            entity_type="entity",
            transaction_id=transaction_id,
        )

        return EntityResponse(data=data, metadata=metadata)

    def _parse_entity_data(self, data: Any, entity_class: str) -> Any:
        """
        Parse entity data using model registry.

        Args:
            data: Raw entity data
            entity_class: Entity class name

        Returns:
            Parsed entity data
        """
        if not data:
            return data

        model_cls = self._model_registry.get(entity_class.lower())
        if model_cls:
            return parse_entity(model_cls, data)
        return data

    def _handle_repository_error(
        self,
        data: Any,
        operation: str,
        entity_class: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> Any:
        """
        Handle repository response errors.

        Args:
            data: Repository response data
            operation: Operation name for logging
            entity_class: Entity class name
            entity_id: Entity ID

        Returns:
            Processed data or raises exception

        Raises:
            EntityServiceError: If repository returned an error
        """
        if isinstance(data, dict) and data.get("errorMessage"):
            error_msg = f"{operation} failed: {data.get('errorMessage')}"
            logger.error(f"{error_msg} - Entity: {entity_class}, ID: {entity_id}")
            raise EntityServiceError(error_msg, entity_class, entity_id)

        return data

    async def _get_repository_meta(
        self,
        token: str,
        entity_class: str,
        entity_version: str,
        additional_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get repository metadata with optional additional metadata.

        Args:
            token: Authentication token
            entity_class: Entity class name
            entity_version: Entity version
            additional_meta: Additional metadata to merge

        Returns:
            Complete metadata dictionary
        """
        meta = await self._repository.get_meta(token, entity_class, entity_version)
        if additional_meta:
            meta.update(additional_meta)
        return meta

    # ========================================
    # PRIMARY RETRIEVAL METHODS
    # ========================================

    async def get_by_id(
        self, entity_id: str, entity_class: str, entity_version: str = "1.0"
    ) -> Optional[EntityResponse]:
        """
        Get entity by technical UUID (FASTEST - use when you have the UUID).

        Args:
            entity_id: Technical UUID
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            EntityResponse with entity and metadata, or None if not found
        """
        try:
            # Use empty token for now - this should be injected properly in production
            meta = await self._get_repository_meta("", entity_class, entity_version)

            data = await self._repository.find_by_id(meta, entity_id)
            if not data:
                return None

            # Handle repository errors
            data = self._handle_repository_error(
                data, "get_by_id", entity_class, entity_id
            )

            # Parse entity data
            parsed_data = self._parse_entity_data(data, entity_class)

            # Create response
            return self._create_entity_response(parsed_data, entity_id)

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(f"Failed to get entity by ID: {entity_id}")
            raise EntityServiceError(
                f"Get by ID failed: {str(e)}", entity_class, entity_id
            )

    async def find_by_business_id(
        self,
        entity_class: str,
        business_id: str,
        business_id_field: str,
        entity_version: str = "1.0",
    ) -> Optional[EntityResponse]:
        """
        Find entity by business identifier (MEDIUM SPEED - use for user-facing IDs).

        Args:
            entity_class: Entity class/model name
            business_id: Business identifier value (e.g., "CART-123")
            business_id_field: Field name containing the business ID (e.g., "cart_id")
            entity_version: Entity model version

        Returns:
            EntityResponse with entity and metadata, or None if not found
        """
        try:
            # Create search condition for business ID
            _ = {business_id_field: business_id}  # kept for clarity; not used directly

            # Use search to find by business ID
            search_request = (
                SearchConditionRequest.builder()
                .equals(business_id_field, business_id)
                .limit(1)
                .build()
            )
            results = await self.search(entity_class, search_request, entity_version)

            return results[0] if results else None

        except Exception as e:
            logger.exception(f"Failed to find entity by business ID: {business_id}")
            raise EntityServiceError(
                f"Find by business ID failed: {str(e)}", entity_class, business_id
            )

    async def find_by_business_id_at_time(
        self,
        entity_class: str,
        business_id: str,
        business_id_field: str,
        point_in_time: datetime,
        entity_version: str = "1.0",
    ) -> Optional[EntityResponse]:
        """
        Find entity by business identifier at a specific point in time.

        Args:
            entity_class: Entity class/model name
            business_id: Business identifier value (e.g., "CART-123")
            business_id_field: Field name containing the business ID (e.g., "cart_id")
            point_in_time: Datetime for temporal query
            entity_version: Entity model version

        Returns:
            EntityResponse with entity and metadata, or None if not found
        """
        try:
            # Use search_at_time to find by business ID
            search_request = (
                SearchConditionRequest.builder()
                .equals(business_id_field, business_id)
                .limit(1)
                .build()
            )
            results = await self.search_at_time(
                entity_class, search_request, point_in_time, entity_version
            )

            return results[0] if results else None

        except Exception as e:
            logger.exception(
                f"Failed to find entity by business ID at time {point_in_time}: {business_id}"
            )
            raise EntityServiceError(
                f"Find by business ID at time failed: {str(e)}",
                entity_class,
                business_id,
            )

    async def find_all(
        self, entity_class: str, entity_version: str = "1.0"
    ) -> List[EntityResponse]:
        """
        Get all entities of a type (SLOW - use sparingly).

        Args:
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            List of EntityResponse with entities and metadata
        """
        try:
            meta = await self._get_repository_meta("", entity_class, entity_version)

            data = await self._repository.find_all(meta)

            # Handle repository errors
            data = self._handle_repository_error(data, "find_all", entity_class)

            if not data:
                return []

            # Parse and create responses
            results: List[EntityResponse] = []
            for item in data if isinstance(data, list) else [data]:
                parsed_item = self._parse_entity_data(item, entity_class)
                response = self._create_entity_response(parsed_item)
                results.append(response)

            logger.debug(f"Found {len(results)} entities of type {entity_class}")
            return results

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(f"Failed to find all entities of type: {entity_class}")
            raise EntityServiceError(f"Find all failed: {str(e)}", entity_class)

    async def find_all_at_time(
        self, entity_class: str, point_in_time: datetime, entity_version: str = "1.0"
    ) -> List[EntityResponse]:
        """
        Get all entities of a type at a specific point in time (SLOW - use sparingly).

        Args:
            entity_class: Entity class/model name
            point_in_time: Datetime for temporal query
            entity_version: Entity model version

        Returns:
            List of EntityResponse with entities and metadata
        """
        try:
            meta = await self._get_repository_meta("", entity_class, entity_version)

            # Use find_all_by_criteria with empty criteria and point_in_time
            # This will return all entities as they existed at the specified time
            data = await self._repository.find_all_by_criteria(meta, {}, point_in_time)

            # Handle repository errors
            data = self._handle_repository_error(data, "find_all_at_time", entity_class)

            if not data:
                return []

            # Parse and create responses
            results: List[EntityResponse] = []
            for item in data if isinstance(data, list) else [data]:
                parsed_item = self._parse_entity_data(item, entity_class)
                response = self._create_entity_response(parsed_item)
                results.append(response)

            logger.debug(
                f"Found {len(results)} entities of type {entity_class} at time {point_in_time}"
            )
            return results

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(
                f"Failed to find all entities at time {point_in_time}: {entity_class}"
            )
            raise EntityServiceError(f"Find all at time failed: {str(e)}", entity_class)

    async def search(
        self,
        entity_class: str,
        condition: SearchConditionRequest,
        entity_version: str = "1.0",
    ) -> List[EntityResponse]:
        """
        Search entities with complex conditions (SLOWEST - most flexible).

        Args:
            entity_class: Entity class/model name
            condition: Search condition
            entity_version: Entity model version

        Returns:
            List of EntityResponse with entities and metadata
        """
        try:
            meta = await self._get_repository_meta("", entity_class, entity_version)

            # Convert SearchConditionRequest to repository format
            criteria = self._convert_search_condition(condition)

            data = await self._repository.find_all_by_criteria(meta, criteria)

            # Handle repository errors
            data = self._handle_repository_error(data, "search", entity_class)

            if not data:
                return []

            # Parse and create responses
            results: List[EntityResponse] = []
            for item in data if isinstance(data, list) else [data]:
                parsed_item = self._parse_entity_data(item, entity_class)
                response = self._create_entity_response(parsed_item)
                results.append(response)

            # Apply limit if specified
            if condition.limit and len(results) > condition.limit:
                results = results[: condition.limit]

            logger.debug(f"Search found {len(results)} entities of type {entity_class}")
            return results

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(f"Failed to search entities of type: {entity_class}")
            raise EntityServiceError(f"Search failed: {str(e)}", entity_class)

    # Reverse mapping: internal SearchOperator value → Cyoda operatorType
    _INTERNAL_TO_CYODA_OPERATOR: Dict[str, str] = {
        "eq": "EQUALS", "ne": "NOT_EQUAL", "ieq": "IEQUALS", "ine": "INOT_EQUAL",
        "is_null": "IS_NULL", "not_null": "NOT_NULL",
        "gt": "GREATER_THAN", "gte": "GREATER_OR_EQUAL",
        "lt": "LESS_THAN", "lte": "LESS_OR_EQUAL",
        "contains": "CONTAINS", "not_contains": "NOT_CONTAINS",
        "startswith": "STARTS_WITH", "not_startswith": "NOT_STARTS_WITH",
        "endswith": "ENDS_WITH", "not_endswith": "NOT_ENDS_WITH",
        "icontains": "ICONTAINS", "inot_contains": "INOT_CONTAINS",
        "istartswith": "ISTARTS_WITH", "inot_startswith": "INOT_STARTS_WITH",
        "iendswith": "IENDS_WITH", "inot_endswith": "INOT_ENDS_WITH",
        "matches_pattern": "MATCHES_PATTERN", "like": "LIKE",
        "between": "BETWEEN", "between_inclusive": "BETWEEN_INCLUSIVE",
        "in": "IN", "not_in": "NOT_IN",
        "is_unchanged": "IS_UNCHANGED", "is_changed": "IS_CHANGED",
    }

    def _convert_search_condition(
        self, condition: SearchConditionRequest
    ) -> Dict[str, Any]:
        """Convert SearchConditionRequest to Cyoda-native search format."""
        if not condition.conditions:
            return {"type": "group", "operator": "AND", "conditions": []}

        cyoda_conditions: List[Dict[str, Any]] = []
        for cond in condition.conditions:
            internal_op = (
                cond.operator.value
                if hasattr(cond.operator, "value")
                else str(cond.operator)
            )
            cyoda_op = self._INTERNAL_TO_CYODA_OPERATOR.get(internal_op, "EQUALS")

            if cond.field in ("state", "current_state"):
                cyoda_conditions.append({
                    "type": "lifecycle",
                    "field": cond.field,
                    "operatorType": cyoda_op,
                    "value": cond.value,
                })
            else:
                json_path = (
                    f"$.{cond.field}"
                    if not cond.field.startswith("$.")
                    else cond.field
                )
                cyoda_conditions.append({
                    "type": "simple",
                    "jsonPath": json_path,
                    "operatorType": cyoda_op,
                    "value": cond.value,
                })

        logical_op = condition.operator.upper() if condition.operator else "AND"
        return {
            "type": "group",
            "operator": logical_op,
            "conditions": cyoda_conditions,
        }

    # ========================================
    # PRIMARY MUTATION METHODS
    # ========================================

    async def save(
        self, entity: Dict[str, Any], entity_class: str, entity_version: str = "1.0"
    ) -> EntityResponse:
        """
        Save a new entity (CREATE operation).

        Args:
            entity: New entity data to save
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            EntityResponse with saved entity and metadata
        """
        try:
            meta = await self._get_repository_meta("", entity_class, entity_version)

            entity_id = await self._repository.save(meta, entity)

            if not entity_id:
                raise EntityServiceError(
                    "Save operation returned no entity ID", entity_class
                )

            # Add technical_id to entity data
            entity_with_id = {**entity, "technical_id": str(entity_id)}

            # Parse entity data
            parsed_entity = self._parse_entity_data(entity_with_id, entity_class)

            # Create response
            response = self._create_entity_response(
                parsed_entity, str(entity_id), "active"
            )

            logger.debug(f"Saved entity {entity_id} of type {entity_class}")
            return response

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(f"Failed to save entity of type: {entity_class}")
            raise EntityServiceError(f"Save failed: {str(e)}", entity_class)

    async def update(
        self,
        entity_id: str,
        entity: Dict[str, Any],
        entity_class: str,
        transition: Optional[str] = None,
        entity_version: str = "1.0",
    ) -> EntityResponse:
        """
        Update existing entity by technical UUID (FASTEST - use when you have UUID).

        Args:
            entity_id: Technical UUID
            entity: Updated entity data
            entity_class: Entity class/model name
            transition: Optional workflow transition name
            entity_version: Entity model version

        Returns:
            EntityResponse with updated entity and metadata
        """
        try:
            additional_meta: Dict[str, Any] = {}
            if transition:
                additional_meta["update_transition"] = transition

            meta = await self._get_repository_meta(
                "", entity_class, entity_version, additional_meta
            )

            updated_id = await self._repository.update(meta, entity_id, entity)

            if not updated_id:
                raise EntityServiceError(
                    "Update operation returned no entity ID", entity_class, entity_id
                )

            # Add technical_id to entity data
            entity_with_id = {**entity, "technical_id": str(updated_id)}

            # Parse entity data
            parsed_entity = self._parse_entity_data(entity_with_id, entity_class)

            # Create response
            response = self._create_entity_response(parsed_entity, str(updated_id))

            logger.debug(f"Updated entity {entity_id} of type {entity_class}")
            return response

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(
                f"Failed to update entity {entity_id} of type: {entity_class}"
            )
            raise EntityServiceError(
                f"Update failed: {str(e)}", entity_class, entity_id
            )

    async def update_by_business_id(
        self,
        entity: Dict[str, Any],
        business_id_field: str,
        entity_class: str,
        transition: Optional[str] = None,
        entity_version: str = "1.0",
    ) -> EntityResponse:
        """
        Update existing entity by business identifier (MEDIUM SPEED).

        Args:
            entity: Updated entity data (must contain business ID)
            business_id_field: Field name containing the business ID
            entity_class: Entity class/model name
            transition: Optional workflow transition name
            entity_version: Entity model version

        Returns:
            EntityResponse with updated entity and metadata
        """
        try:
            business_id = entity.get(business_id_field)
            if not business_id:
                raise EntityServiceError(
                    f"Entity data missing required field: {business_id_field}",
                    entity_class,
                )

            # Find existing entity
            existing = await self.find_by_business_id(
                entity_class, str(business_id), business_id_field, entity_version
            )
            if not existing:
                raise EntityServiceError(
                    f"Entity not found with {business_id_field}={business_id}",
                    entity_class,
                    str(business_id),
                )

            # Update using technical ID
            return await self.update(
                existing.get_id(), entity, entity_class, transition, entity_version
            )

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(
                f"Failed to update entity by business ID: {entity.get(business_id_field)}"
            )
            raise EntityServiceError(
                f"Update by business ID failed: {str(e)}", entity_class
            )

    async def delete_by_id(
        self, entity_id: str, entity_class: str, entity_version: str = "1.0"
    ) -> str:
        """
        Delete entity by technical UUID (FASTEST).

        Args:
            entity_id: Technical UUID to delete
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            UUID of deleted entity
        """
        try:
            meta = await self._get_repository_meta("", entity_class, entity_version)

            await self._repository.delete_by_id(meta, entity_id)

            logger.debug(f"Deleted entity {entity_id} of type {entity_class}")
            return entity_id

        except Exception as e:
            logger.exception(
                f"Failed to delete entity {entity_id} of type: {entity_class}"
            )
            raise EntityServiceError(
                f"Delete failed: {str(e)}", entity_class, entity_id
            )

    async def delete_by_business_id(
        self,
        entity_class: str,
        business_id: str,
        business_id_field: str,
        entity_version: str = "1.0",
    ) -> bool:
        """
        Delete entity by business identifier.

        Args:
            entity_class: Entity class/model name
            business_id: Business identifier value
            business_id_field: Field name containing the business ID
            entity_version: Entity model version

        Returns:
            True if deleted, False if not found
        """
        try:
            # Find existing entity
            existing = await self.find_by_business_id(
                entity_class, business_id, business_id_field, entity_version
            )
            if not existing:
                return False

            # Delete using technical ID
            await self.delete_by_id(existing.get_id(), entity_class, entity_version)
            return True

        except Exception as e:
            logger.exception(f"Failed to delete entity by business ID: {business_id}")
            raise EntityServiceError(
                f"Delete by business ID failed: {str(e)}", entity_class, business_id
            )

    # ========================================
    # BATCH OPERATIONS
    # ========================================

    async def save_all(
        self,
        entities: List[Dict[str, Any]],
        entity_class: str,
        entity_version: str = "1.0",
    ) -> List[EntityResponse]:
        """
        Save multiple entities in batch.

        Args:
            entities: List of entities to save
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            List of EntityResponse with saved entities and metadata
        """
        try:
            if not entities:
                return []

            meta = await self._get_repository_meta("", entity_class, entity_version)

            # Use repository batch save if available, otherwise save individually
            if hasattr(self._repository, "save_all"):
                batch_base_id = await self._repository.save_all(meta, entities)
                # For batch operations, we might only get a base ID
                results: List[EntityResponse] = []
                for i, entity in enumerate(entities):
                    current_id = (
                        f"{batch_base_id}_{i}" if batch_base_id else f"batch_{i}"
                    )
                    entity_with_id = {**entity, "technical_id": current_id}
                    parsed_entity = self._parse_entity_data(
                        entity_with_id, entity_class
                    )
                    response = self._create_entity_response(
                        parsed_entity, current_id, "active"
                    )
                    results.append(response)
                return results
            else:
                # Save individually
                results = []
                for entity in entities:
                    result = await self.save(entity, entity_class, entity_version)
                    results.append(result)
                return results

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(
                f"Failed to save batch of {len(entities)} entities of type: {entity_class}"
            )
            raise EntityServiceError(f"Batch save failed: {str(e)}", entity_class)

    async def delete_all(self, entity_class: str, entity_version: str = "1.0") -> int:
        """
        Delete all entities of a type (DANGEROUS - use with caution).

        Args:
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            Number of entities deleted
        """
        try:
            # First count existing entities
            existing_entities = await self.find_all(entity_class, entity_version)
            count = len(existing_entities)

            if count == 0:
                return 0

            meta = await self._get_repository_meta("", entity_class, entity_version)
            await self._repository.delete_all(meta)

            logger.warning(f"Deleted ALL {count} entities of type {entity_class}")
            return count

        except Exception as e:
            logger.exception(f"Failed to delete all entities of type: {entity_class}")
            raise EntityServiceError(f"Delete all failed: {str(e)}", entity_class)

    # ========================================
    # WORKFLOW AND TRANSITION METHODS
    # ========================================

    async def get_transitions(
        self, entity_id: str, entity_class: str, entity_version: str = "1.0"
    ) -> List[str]:
        """
        Get available transitions for an entity.

        Args:
            entity_id: Technical UUID of the entity
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            List of available transition names
        """
        try:
            meta = await self._get_repository_meta("", entity_class, entity_version)

            if hasattr(self._repository, "get_transitions"):
                transitions = await self._repository.get_transitions(meta, entity_id)
                if isinstance(transitions, list):
                    return [str(t) for t in transitions]
                elif isinstance(transitions, dict):
                    return [str(k) for k in transitions.keys()]
                else:
                    return []
            else:
                # Return default transitions if repository doesn't support it
                return ["update", "complete", "cancel"]

        except Exception as e:
            logger.exception(f"Failed to get transitions for entity {entity_id}")
            raise EntityServiceError(
                f"Get transitions failed: {str(e)}", entity_class, entity_id
            )

    async def execute_transition(
        self,
        entity_id: str,
        transition: str,
        entity_class: str,
        entity_version: str = "1.0",
    ) -> EntityResponse:
        """
        Execute a workflow transition on an entity.

        Args:
            entity_id: Technical UUID of the entity
            transition: Transition name to execute
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            EntityResponse with updated entity and metadata
        """
        try:
            # Get current entity
            current_entity = await self.get_by_id(
                entity_id, entity_class, entity_version
            )
            if not current_entity:
                raise EntityServiceError(
                    f"Entity not found: {entity_id}", entity_class, entity_id
                )

            # Execute transition by updating with transition
            if hasattr(current_entity.data, "model_dump"):
                entity_data: Dict[str, Any] = current_entity.data.model_dump(
                    by_alias=True
                )
            else:
                entity_data = cast(Dict[str, Any], current_entity.data)
            return await self.update(
                entity_id, entity_data, entity_class, transition, entity_version
            )

        except EntityServiceError:
            raise
        except Exception as e:
            logger.exception(
                f"Failed to execute transition {transition} on entity {entity_id}"
            )
            raise EntityServiceError(
                f"Execute transition failed: {str(e)}", entity_class, entity_id
            )

    # ========================================
    # TEMPORAL AND STATISTICS METHODS
    # ========================================

    async def get_by_id_at_time(
        self,
        entity_id: str,
        entity_class: str,
        point_in_time: datetime,
        entity_version: str = "1",
    ) -> Optional[EntityResponse]:
        """
        Get entity by technical UUID at a specific point in time.

        Args:
            entity_id: Technical UUID from EntityResponse.metadata.id
            entity_class: Entity class/model name
            point_in_time: Datetime for temporal query
            entity_version: Entity model version

        Returns:
            EntityResponse with entity and metadata, or None if not found
        """
        try:
            meta = await self._get_repository_meta("", entity_class, entity_version)
            entity_data = await self._repository.find_by_id(
                meta, entity_id, point_in_time
            )

            if entity_data is None:
                return None

            # Parse entity data
            parsed_entity = self._parse_entity_data(entity_data, entity_class)

            # Create response
            return self._create_entity_response(parsed_entity, entity_id)

        except Exception as e:
            logger.exception(
                f"Failed to get entity {entity_id} at time {point_in_time}"
            )
            raise EntityServiceError(
                f"Get by ID at time failed: {str(e)}", entity_class, entity_id
            )

    async def search_at_time(
        self,
        entity_class: str,
        condition: SearchConditionRequest,
        point_in_time: datetime,
        entity_version: str = "1",
    ) -> List[EntityResponse]:
        """
        Search entities at a specific point in time.

        Args:
            entity_class: Entity class/model name
            condition: Search condition
            point_in_time: Datetime for temporal query
            entity_version: Entity model version

        Returns:
            List of EntityResponse with entities and metadata
        """
        try:
            meta = await self._get_repository_meta("", entity_class, entity_version)

            # Convert SearchConditionRequest to criteria format
            criteria = self._convert_search_condition(condition)

            # Search with point_in_time
            entities = await self._repository.find_all_by_criteria(
                meta, criteria, point_in_time
            )

            # Convert to EntityResponse objects
            results: List[EntityResponse] = []
            for entity_data in entities:
                parsed_entity = self._parse_entity_data(entity_data, entity_class)
                response = self._create_entity_response(parsed_entity)
                results.append(response)

            return results

        except Exception as e:
            logger.exception(f"Failed to search {entity_class} at time {point_in_time}")
            raise EntityServiceError(f"Search at time failed: {str(e)}", entity_class)

    async def get_entity_count(
        self,
        entity_class: str,
        entity_version: str = "1",
        point_in_time: Optional[datetime] = None,
    ) -> int:
        """
        Get count of entities for a specific model, optionally at a point in time.

        Args:
            entity_class: Entity class/model name
            entity_version: Entity model version
            point_in_time: Optional datetime for temporal queries

        Returns:
            Number of entities
        """
        try:
            meta = await self._repository.get_meta("", entity_class, entity_version)
            return await self._repository.get_entity_count(meta, point_in_time)

        except Exception:
            logger.exception(f"Failed to get entity count for {entity_class}")
            return 0

    async def get_entity_changes_metadata(
        self,
        entity_id: str,
        entity_class: str,
        entity_version: str = "1",
        point_in_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get entity change history metadata.

        Args:
            entity_id: Technical UUID of the entity
            entity_class: Entity class/model name
            entity_version: Entity model version
            point_in_time: Optional datetime for temporal queries

        Returns:
            List of change metadata entries
        """
        try:
            return await self._repository.get_entity_changes_metadata(
                entity_id, point_in_time
            )

        except Exception:
            logger.exception(f"Failed to get entity changes metadata for {entity_id}")
            return []

    # ========================================
    # LEGACY COMPATIBILITY METHODS
    # ========================================

    async def get_item(  # deprecated
        self,
        token: str,
        entity_model: str,
        entity_version: str,
        technical_id: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        @deprecated Use get_by_id() instead for better clarity

        Legacy method for backward compatibility.
        """
        import warnings

        warnings.warn(
            "get_item() is deprecated, use get_by_id() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            result = await self.get_by_id(technical_id, entity_model, entity_version)
            return result.data if result else None
        except EntityServiceError:
            return None
        except Exception as e:
            logger.exception(f"Legacy get_item failed: {e}")
            return None

    async def get_items(  # deprecated
        self, token: str, entity_model: str, entity_version: str
    ) -> List[Any]:
        """
        @deprecated Use find_all() instead for better clarity

        Legacy method for backward compatibility.
        """
        import warnings

        warnings.warn(
            "get_items() is deprecated, use find_all() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            results = await self.find_all(entity_model, entity_version)
            return [result.data for result in results]
        except EntityServiceError:
            return []
        except Exception as e:
            logger.exception(f"Legacy get_items failed: {e}")
            return []

    async def get_single_item_by_condition(  # deprecated
        self, token: str, entity_model: str, entity_version: str, condition: Any
    ) -> Optional[Any]:
        """
        @deprecated Use search() instead for better clarity

        Legacy method for backward compatibility.
        """
        import warnings

        warnings.warn(
            "get_single_item_by_condition() is deprecated, use search() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            # Convert legacy condition to SearchConditionRequest
            search_request = self._convert_legacy_condition(condition)
            search_request.limit = 1

            results = await self.search(entity_model, search_request, entity_version)
            return results[0].data if results else None
        except EntityServiceError:
            return None
        except Exception as e:
            logger.exception(f"Legacy get_single_item_by_condition failed: {e}")
            return None

    async def get_items_by_condition(  # deprecated
        self, token: str, entity_model: str, entity_version: str, condition: Any
    ) -> List[Any]:
        """
        @deprecated Use search() instead for better clarity

        Legacy method for backward compatibility.
        """
        import warnings

        warnings.warn(
            "get_items_by_condition() is deprecated, use search() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            # Handle legacy condition format
            if isinstance(condition, dict) and CHAT_REPOSITORY in condition:
                actual_condition = condition.get(CHAT_REPOSITORY)
            else:
                actual_condition = condition

            # Convert legacy condition to SearchConditionRequest
            search_request = self._convert_legacy_condition(actual_condition)

            results = await self.search(entity_model, search_request, entity_version)
            return [result.data for result in results]
        except EntityServiceError:
            return []
        except Exception as e:
            logger.exception(f"Legacy get_items_by_condition failed: {e}")
            return []

    async def add_item(  # deprecated
        self,
        token: str,
        entity_model: str,
        entity_version: str,
        entity: Any,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        @deprecated Use save() instead for better clarity

        Legacy method for backward compatibility.
        """
        import warnings

        warnings.warn(
            "add_item() is deprecated, use save() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            result = await self.save(entity, entity_model, entity_version)
            return result.get_id()
        except EntityServiceError:
            return None
        except Exception as e:
            logger.exception(f"Legacy add_item failed: {e}")
            return None

    async def update_item(  # deprecated
        self,
        token: str,
        entity_model: str,
        entity_version: str,
        technical_id: str,
        entity: Any,
        meta: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """
        @deprecated Use update() instead for better clarity

        Legacy method for backward compatibility.
        """
        import warnings

        warnings.warn(
            "update_item() is deprecated, use update() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            transition = (
                meta.get("update_transition") if isinstance(meta, dict) else None
            )
            result = await self.update(
                technical_id, entity, entity_model, transition, entity_version
            )
            return result.get_id()
        except EntityServiceError:
            return None
        except Exception as e:
            logger.exception(f"Legacy update_item failed: {e}")
            return None

    async def delete_item(  # deprecated
        self,
        token: str,
        entity_model: str,
        entity_version: str,
        technical_id: str,
        meta: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """
        @deprecated Use delete_by_id() instead for better clarity

        Legacy method for backward compatibility.
        """
        import warnings

        warnings.warn(
            "delete_item() is deprecated, use delete_by_id() instead",
            DeprecationWarning,
            stacklevel=2,
        )

        try:
            deleted_id = await self.delete_by_id(
                technical_id, entity_model, entity_version
            )
            return deleted_id
        except EntityServiceError:
            return None
        except Exception as e:
            logger.exception(f"Legacy delete_item failed: {e}")
            return None

    def _convert_legacy_condition(self, condition: Any) -> SearchConditionRequest:
        """
        Convert legacy condition format to SearchConditionRequest.

        Args:
            condition: Legacy condition format

        Returns:
            SearchConditionRequest object
        """
        builder = SearchConditionRequest.builder()

        if isinstance(condition, dict):
            for key, value in condition.items():
                builder.equals(key, value)
        elif isinstance(condition, str):
            # Assume it's a simple string condition
            builder.equals("name", condition)

        return builder.build()

    async def _find_by_criteria(
        self, token: str, entity_model: str, entity_version: str, condition: Any
    ) -> List[Any]:
        """Internal method for legacy compatibility."""
        try:
            search_request = self._convert_legacy_condition(condition)
            results = await self.search(entity_model, search_request, entity_version)
            return [result.data for result in results]
        except Exception as e:
            logger.exception(f"Internal _find_by_criteria failed: {e}")
            return []
