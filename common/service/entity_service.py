"""
Entity Service Interface

Simplified EntityService interface with clear method selection guidance.
Aligned with Java EntityService interface for consistency across platforms.

METHOD SELECTION GUIDE:

FOR RETRIEVAL:
- Use get_by_id() when you have the technical UUID (fastest, most efficient)
- Use find_by_business_id() when you have a business identifier (e.g., "CART-123", "PAY-456")
- Use find_all() to get all entities of a type (use sparingly, can be slow)
- Use search() for complex queries with multiple conditions

FOR MUTATIONS:
- Use save() for new entities
- Use update() for existing entities with technical UUID
- Use update_by_business_id() for existing entities with business identifier

PERFORMANCE NOTES:
- Technical UUID operations are fastest (direct lookup)
- Business ID operations require field search (slower)
- Complex search operations are slowest but most flexible
- Always prefer direct UUID operations when possible
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from common.entity.cyoda_entity import CyodaEntity


class SearchOperator(Enum):
    """Search operators for entity queries."""

    # Equality operators
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    IEQUALS = "ieq"  # Case-insensitive equals
    INOT_EQUALS = "ine"  # Case-insensitive not equals

    # Null checks
    IS_NULL = "is_null"
    NOT_NULL = "not_null"

    # Comparison operators
    GREATER_THAN = "gt"
    GREATER_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_OR_EQUAL = "lte"

    # Text operators
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "startswith"
    NOT_STARTS_WITH = "not_startswith"
    ENDS_WITH = "endswith"
    NOT_ENDS_WITH = "not_endswith"

    # Case-insensitive text operators
    ICONTAINS = "icontains"
    INOT_CONTAINS = "inot_contains"
    ISTARTS_WITH = "istartswith"
    INOT_STARTS_WITH = "inot_startswith"
    IENDS_WITH = "iendswith"
    INOT_ENDS_WITH = "inot_endswith"

    # Pattern matching
    MATCHES_PATTERN = "matches_pattern"
    LIKE = "like"

    # Range operators
    BETWEEN = "between"
    BETWEEN_INCLUSIVE = "between_inclusive"

    # List operators
    IN = "in"
    NOT_IN = "not_in"

    # Change detection
    IS_UNCHANGED = "is_unchanged"
    IS_CHANGED = "is_changed"


class CyodaOperator(Enum):
    """Cyoda search operators mapping to internal operators."""

    # Equality operators
    EQUALS = "EQUALS"
    NOT_EQUAL = "NOT_EQUAL"
    IEQUALS = "IEQUALS"
    INOT_EQUAL = "INOT_EQUAL"

    # Null checks
    IS_NULL = "IS_NULL"
    NOT_NULL = "NOT_NULL"

    # Comparison operators
    GREATER_THAN = "GREATER_THAN"
    GREATER_OR_EQUAL = "GREATER_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_OR_EQUAL = "LESS_OR_EQUAL"

    # Text operators
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    NOT_STARTS_WITH = "NOT_STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    NOT_ENDS_WITH = "NOT_ENDS_WITH"

    # Case-insensitive text operators
    ICONTAINS = "ICONTAINS"
    ISTARTS_WITH = "ISTARTS_WITH"
    IENDS_WITH = "IENDS_WITH"
    INOT_CONTAINS = "INOT_CONTAINS"
    INOT_STARTS_WITH = "INOT_STARTS_WITH"
    INOT_ENDS_WITH = "INOT_ENDS_WITH"

    # Pattern matching
    MATCHES_PATTERN = "MATCHES_PATTERN"
    LIKE = "LIKE"

    # Range operators
    BETWEEN = "BETWEEN"
    BETWEEN_INCLUSIVE = "BETWEEN_INCLUSIVE"

    # Change detection
    IS_UNCHANGED = "IS_UNCHANGED"
    IS_CHANGED = "IS_CHANGED"


class LogicalOperator(Enum):
    """Logical operators for combining search conditions."""

    AND = "and"
    OR = "or"


# Mapping from Cyoda operators to internal SearchOperator
CYODA_OPERATOR_MAPPING = {
    CyodaOperator.EQUALS.value: SearchOperator.EQUALS,
    CyodaOperator.NOT_EQUAL.value: SearchOperator.NOT_EQUALS,
    CyodaOperator.IEQUALS.value: SearchOperator.IEQUALS,
    CyodaOperator.INOT_EQUAL.value: SearchOperator.INOT_EQUALS,
    CyodaOperator.IS_NULL.value: SearchOperator.IS_NULL,
    CyodaOperator.NOT_NULL.value: SearchOperator.NOT_NULL,
    CyodaOperator.GREATER_THAN.value: SearchOperator.GREATER_THAN,
    CyodaOperator.GREATER_OR_EQUAL.value: SearchOperator.GREATER_OR_EQUAL,
    CyodaOperator.LESS_THAN.value: SearchOperator.LESS_THAN,
    CyodaOperator.LESS_OR_EQUAL.value: SearchOperator.LESS_OR_EQUAL,
    CyodaOperator.CONTAINS.value: SearchOperator.CONTAINS,
    CyodaOperator.NOT_CONTAINS.value: SearchOperator.NOT_CONTAINS,
    CyodaOperator.STARTS_WITH.value: SearchOperator.STARTS_WITH,
    CyodaOperator.NOT_STARTS_WITH.value: SearchOperator.NOT_STARTS_WITH,
    CyodaOperator.ENDS_WITH.value: SearchOperator.ENDS_WITH,
    CyodaOperator.NOT_ENDS_WITH.value: SearchOperator.NOT_ENDS_WITH,
    CyodaOperator.ICONTAINS.value: SearchOperator.ICONTAINS,
    CyodaOperator.ISTARTS_WITH.value: SearchOperator.ISTARTS_WITH,
    CyodaOperator.IENDS_WITH.value: SearchOperator.IENDS_WITH,
    CyodaOperator.INOT_CONTAINS.value: SearchOperator.INOT_CONTAINS,
    CyodaOperator.INOT_STARTS_WITH.value: SearchOperator.INOT_STARTS_WITH,
    CyodaOperator.INOT_ENDS_WITH.value: SearchOperator.INOT_ENDS_WITH,
    CyodaOperator.MATCHES_PATTERN.value: SearchOperator.MATCHES_PATTERN,
    CyodaOperator.LIKE.value: SearchOperator.LIKE,
    CyodaOperator.BETWEEN.value: SearchOperator.BETWEEN,
    CyodaOperator.BETWEEN_INCLUSIVE.value: SearchOperator.BETWEEN_INCLUSIVE,
    CyodaOperator.IS_UNCHANGED.value: SearchOperator.IS_UNCHANGED,
    CyodaOperator.IS_CHANGED.value: SearchOperator.IS_CHANGED,
}


@dataclass
class EntityMetadata:
    """Entity metadata containing technical information."""

    id: str  # Technical UUID
    state: Optional[str] = None
    version: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    entity_type: Optional[str] = None
    transaction_id: Optional[str] = None


@dataclass
class EntityResponse:
    """Response wrapper containing entity data and metadata."""

    data: CyodaEntity  # The actual entity data as a Pydantic model
    metadata: EntityMetadata

    def get_id(self) -> str:
        """Get technical UUID."""
        return self.metadata.id

    def get_state(self) -> Optional[str]:
        """Get entity state."""
        return self.metadata.state


@dataclass
class SearchCondition:
    """Search condition for entity queries."""

    field: str
    operator: SearchOperator  # Use SearchOperator enum
    value: Any


@dataclass
class SearchConditionRequest:
    """Complex search request with multiple conditions."""

    conditions: List[SearchCondition]
    operator: str = "and"  # "and" or "or"
    limit: Optional[int] = None
    offset: Optional[int] = None

    @classmethod
    def builder(cls) -> "SearchConditionRequestBuilder":
        """Create a builder for SearchConditionRequest."""
        return SearchConditionRequestBuilder()


class SearchConditionRequestBuilder:
    """Builder for SearchConditionRequest."""

    def __init__(self) -> None:
        self._conditions: List[SearchCondition] = []
        self._operator = "and"
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def add_condition(
        self, field: str, operator: SearchOperator, value: Any
    ) -> "SearchConditionRequestBuilder":
        """Add a search condition."""
        self._conditions.append(SearchCondition(field, operator, value))
        return self

    def equals(self, field: str, value: Any) -> "SearchConditionRequestBuilder":
        """Add equals condition."""
        return self.add_condition(field, SearchOperator.EQUALS, value)

    def contains(self, field: str, value: str) -> "SearchConditionRequestBuilder":
        """Add contains condition."""
        return self.add_condition(field, SearchOperator.CONTAINS, value)

    def in_values(
        self, field: str, values: List[Any]
    ) -> "SearchConditionRequestBuilder":
        """Add 'in' condition."""
        return self.add_condition(field, SearchOperator.IN, values)

    def operator(self, op: LogicalOperator) -> "SearchConditionRequestBuilder":
        """Set logical operator (and/or)."""
        self._operator = op.value
        return self

    def limit(self, limit: int) -> "SearchConditionRequestBuilder":
        """Set result limit."""
        self._limit = limit
        return self

    def offset(self, offset: int) -> "SearchConditionRequestBuilder":
        """Set result offset."""
        self._offset = offset
        return self

    def build(self) -> SearchConditionRequest:
        """Build the search request."""
        return SearchConditionRequest(
            conditions=self._conditions,
            operator=self._operator,
            limit=self._limit,
            offset=self._offset,
        )


class EntityService(ABC):
    """
    Simplified EntityService interface with clear method selection guidance.

    This interface provides a clean, consistent API for entity operations
    with performance guidance and clear method selection criteria.
    """

    # ========================================
    # PRIMARY RETRIEVAL METHODS (Use These)
    # ========================================

    @abstractmethod
    async def get_by_id(
        self, entity_id: str, entity_class: str, entity_version: str = "1"
    ) -> Optional[EntityResponse]:
        """
        Get entity by technical UUID (FASTEST - use when you have the UUID).

        Args:
            entity_id: Technical UUID from EntityResponse.metadata.id
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            EntityResponse with entity and metadata, or None if not found
        """
        pass

    @abstractmethod
    async def find_by_business_id(
        self,
        entity_class: str,
        business_id: str,
        business_id_field: str,
        entity_version: str = "1",
    ) -> Optional[EntityResponse]:
        """
        Find entity by business identifier (MEDIUM SPEED - use for user-facing IDs).
        Examples: cart_id="CART-123", payment_id="PAY-456", order_id="ORD-789"

        Args:
            entity_class: Entity class/model name
            business_id: Business identifier value (e.g., "CART-123")
            business_id_field: Field name containing the business ID (e.g., "cart_id")
            entity_version: Entity model version

        Returns:
            EntityResponse with entity and metadata, or None if not found
        """
        pass

    @abstractmethod
    async def find_by_business_id_at_time(
        self,
        entity_class: str,
        business_id: str,
        business_id_field: str,
        point_in_time: datetime,
        entity_version: str = "1",
    ) -> Optional[EntityResponse]:
        """
        Find entity by business identifier at a specific point in time (MEDIUM SPEED).
        Examples: cart_id="CART-123", payment_id="PAY-456", order_id="ORD-789"

        Args:
            entity_class: Entity class/model name
            business_id: Business identifier value (e.g., "CART-123")
            business_id_field: Field name containing the business ID (e.g., "cart_id")
            point_in_time: Datetime for temporal query
            entity_version: Entity model version

        Returns:
            EntityResponse with entity and metadata, or None if not found
        """
        pass

    @abstractmethod
    async def find_all(
        self, entity_class: str, entity_version: str = "1"
    ) -> List[EntityResponse]:
        """
        Get all entities of a type (SLOW - use sparingly).

        Args:
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            List of EntityResponse with entities and metadata
        """
        pass

    @abstractmethod
    async def find_all_at_time(
        self, entity_class: str, point_in_time: datetime, entity_version: str = "1"
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
        pass

    @abstractmethod
    async def search(
        self,
        entity_class: str,
        condition: SearchConditionRequest,
        entity_version: str = "1",
    ) -> List[EntityResponse]:
        """
        Search entities with complex conditions (SLOWEST - most flexible).
        Use for advanced queries with multiple conditions, filtering, etc.

        Args:
            entity_class: Entity class/model name
            condition: Search condition (use SearchConditionRequest.builder())
            entity_version: Entity model version

        Returns:
            List of EntityResponse with entities and metadata
        """
        pass

    # ========================================
    # PRIMARY MUTATION METHODS (Use These)
    # ========================================

    @abstractmethod
    async def save(
        self, entity: Dict[str, Any], entity_class: str, entity_version: str = "1"
    ) -> EntityResponse:
        """
        Save a new entity (CREATE operation).

        Args:
            entity: New entity data to save
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            EntityResponse with saved entity and metadata (including technical UUID)
        """
        pass

    @abstractmethod
    async def update(
        self,
        entity_id: str,
        entity: Dict[str, Any],
        entity_class: str,
        transition: Optional[str] = None,
        entity_version: str = "1",
    ) -> EntityResponse:
        """
        Update existing entity by technical UUID (FASTEST - use when you have UUID).

        Args:
            entity_id: Technical UUID from EntityResponse.metadata.id
            entity: Updated entity data
            entity_class: Entity class/model name
            transition: Optional workflow transition name (None to stay in same state)
            entity_version: Entity model version

        Returns:
            EntityResponse with updated entity and metadata
        """
        pass

    @abstractmethod
    async def update_by_business_id(
        self,
        entity: Dict[str, Any],
        business_id_field: str,
        entity_class: str,
        transition: Optional[str] = None,
        entity_version: str = "1",
    ) -> EntityResponse:
        """
        Update existing entity by business identifier (MEDIUM SPEED).

        Args:
            entity: Updated entity data (must contain business ID)
            business_id_field: Field name containing the business ID (e.g., "cart_id")
            entity_class: Entity class/model name
            transition: Optional workflow transition name (None to stay in same state)
            entity_version: Entity model version

        Returns:
            EntityResponse with updated entity and metadata
        """
        pass

    @abstractmethod
    async def delete_by_id(
        self, entity_id: str, entity_class: str, entity_version: str = "1"
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
        pass

    @abstractmethod
    async def delete_by_business_id(
        self,
        entity_class: str,
        business_id: str,
        business_id_field: str,
        entity_version: str = "1",
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
        pass

    # ========================================
    # BATCH OPERATIONS (Use Sparingly)
    # ========================================

    @abstractmethod
    async def save_all(
        self,
        entities: List[Dict[str, Any]],
        entity_class: str,
        entity_version: str = "1",
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
        pass

    @abstractmethod
    async def delete_all(self, entity_class: str, entity_version: str = "1") -> int:
        """
        Delete all entities of a type (DANGEROUS - use with caution).

        Args:
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            Number of entities deleted
        """
        pass

    # ========================================
    # WORKFLOW AND TRANSITION METHODS
    # ========================================

    @abstractmethod
    async def get_transitions(
        self, entity_id: str, entity_class: str, entity_version: str = "1"
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
        pass

    @abstractmethod
    async def execute_transition(
        self,
        entity_id: str,
        transition: str,
        entity_class: str,
        entity_version: str = "1",
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
        pass

    # ========================================
    # UTILITY METHODS
    # ========================================

    async def exists_by_id(
        self, entity_id: str, entity_class: str, entity_version: str = "1"
    ) -> bool:
        """
        Check if entity exists by technical UUID.

        Args:
            entity_id: Technical UUID to check
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            True if entity exists, False otherwise
        """
        try:
            result = await self.get_by_id(entity_id, entity_class, entity_version)
            return result is not None
        except Exception:
            return False

    async def exists_by_business_id(
        self,
        entity_class: str,
        business_id: str,
        business_id_field: str,
        entity_version: str = "1",
    ) -> bool:
        """
        Check if entity exists by business identifier.

        Args:
            entity_class: Entity class/model name
            business_id: Business identifier value
            business_id_field: Field name containing the business ID
            entity_version: Entity model version

        Returns:
            True if entity exists, False if not found
        """
        try:
            result = await self.find_by_business_id(
                entity_class, business_id, business_id_field, entity_version
            )
            return result is not None
        except Exception:
            return False

    async def count(self, entity_class: str, entity_version: str = "1") -> int:
        """
        Count entities of a specific type.

        Args:
            entity_class: Entity class/model name
            entity_version: Entity model version

        Returns:
            Number of entities
        """
        try:
            entities = await self.find_all(entity_class, entity_version)
            return len(entities)
        except Exception:
            return 0

    # ========================================
    # TEMPORAL AND STATISTICS METHODS
    # ========================================

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    # ========================================
    # LEGACY COMPATIBILITY METHODS
    # ========================================

    async def get_item(
        self,
        token: str,
        entity_model: str,
        entity_version: str,
        technical_id: str,
        meta: Any = None,
    ) -> Any:
        """
        @deprecated Use get_by_id() instead for better clarity
        """
        import warnings

        warnings.warn(
            "get_item() is deprecated, use get_by_id() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        result = await self.get_by_id(technical_id, entity_model, entity_version)
        return result.data if result else None

    async def get_items(
        self, token: str, entity_model: str, entity_version: str
    ) -> List[Any]:
        """
        @deprecated Use find_all() instead for better clarity
        """
        import warnings

        warnings.warn(
            "get_items() is deprecated, use find_all() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        results = await self.find_all(entity_model, entity_version)
        return [result.data for result in results]

    async def get_items_by_condition(
        self, token: str, entity_model: str, entity_version: str, condition: Any
    ) -> List[Any]:
        """
        @deprecated Use search() instead for better clarity
        """
        import warnings

        warnings.warn(
            "get_items_by_condition() is deprecated, use search() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        # Convert legacy condition to SearchConditionRequest if needed
        if isinstance(condition, dict):
            search_request = SearchConditionRequest.builder()
            for key, value in condition.items():
                search_request.equals(key, value)
            condition = search_request.build()

        results = await self.search(entity_model, condition, entity_version)
        return [result.data for result in results]
