"""
Cyoda Repository Implementation

Thread-safe repository for interacting with the Cyoda API.
Provides CRUD operations with proper error handling and caching.
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, cast

from common.config.config import CYODA_ENTITY_TYPE_EDGE_MESSAGE
from common.config.conts import (
    EDGE_MESSAGE_CLASS,
    TREE_NODE_ENTITY_CLASS,
    UPDATE_TRANSITION,
)
from common.repository.crud_repository import CrudRepository
from common.utils.utils import custom_serializer, send_cyoda_request

logger = logging.getLogger(__name__)

# In-memory cache for edge-message entities
_edge_messages_cache: Dict[str, Any] = {}


class CyodaRepository(CrudRepository[Any]):  # type: ignore[type-arg]
    """
    Thread-safe singleton repository for interacting with the Cyoda API.
    Provides CRUD operations with caching and error handling.
    """

    _instance: Optional["CyodaRepository"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, cyoda_auth_service: Any) -> None:
        """Initialize the repository."""
        self._cyoda_auth_service: Any = cyoda_auth_service

    def __new__(cls, cyoda_auth_service: Any) -> "CyodaRepository":  # type: ignore[override]
        """Thread-safe singleton implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._cyoda_auth_service = cyoda_auth_service
        return cls._instance

    # -----------------------
    # Small internal helpers
    # -----------------------

    @staticmethod
    def _json_loads_or_empty(content: str) -> Dict[str, Any]:
        """Safe JSON parse that never raises; returns empty dict on error."""
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}

    @staticmethod
    def _extract_technical_id_from_result(result: Any) -> Optional[str]:
        """
        Extract the first technical ID from a typical Cyoda 'json' result payload
        which is a list like: [{'entityIds': ['...']}].
        """
        if isinstance(result, list) and result:
            first = result[0] or {}
            if isinstance(first, dict):
                ids = first.get("entityIds", [None])
                if isinstance(ids, list) and ids and ids[0] is not None:
                    return str(ids[0])
        return None

    @staticmethod
    def _coerce_list_of_dicts(value: Any) -> List[Dict[str, Any]]:
        """Return a list of dicts or an empty list if shape isn't as expected."""
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        return []

    @staticmethod
    def _ensure_technical_id_on_entities(
        entities: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Ensure each entity has a 'technical_id' field derived from meta.id or id."""
        out: List[Dict[str, Any]] = []
        for e in entities:
            if "technical_id" not in e or e.get("technical_id") in (None, ""):
                meta = e.get("meta", {})
                if isinstance(meta, dict) and "id" in meta:
                    e["technical_id"] = meta["id"]
                elif "id" in e:
                    e["technical_id"] = e["id"]
            out.append(e)
        return out

    async def _wait_for_search_completion(
        self, snapshot_id: str, timeout: float = 60.0, interval: float = 0.3
    ) -> None:
        """Poll the snapshot status endpoint until SUCCESSFUL or error/timeout."""
        start = time.monotonic()
        status_path = f"search/snapshot/{snapshot_id}/status"

        while True:
            resp: Dict[str, Any] = await send_cyoda_request(
                cyoda_auth_service=self._cyoda_auth_service,
                method="get",
                path=status_path,
            )
            if resp.get("status") != 200:
                return
            status = resp.get("json", {}).get("snapshotStatus")
            if status == "SUCCESSFUL":
                return
            if status not in ("RUNNING",):
                raise Exception(f"Snapshot search failed: {resp.get('json')}")
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"Timeout exceeded after {timeout} seconds")
            await asyncio.sleep(interval)

    # -----------------------
    # CRUD Repository Methods
    # -----------------------

    async def find_by_id(
        self,
        meta: Optional[Dict[str, Any]],
        entity_id: Any,
        point_in_time: Optional[datetime] = None,
    ) -> Optional[Any]:
        """Find entity by ID, optionally at a specific point in time."""
        if meta and meta.get("type") == CYODA_ENTITY_TYPE_EDGE_MESSAGE:
            key = str(entity_id)
            if key in _edge_messages_cache:
                return _edge_messages_cache[key]
            path = f"message/get/{entity_id}"
            resp: Dict[str, Any] = await send_cyoda_request(
                cyoda_auth_service=self._cyoda_auth_service, method="get", path=path
            )
            content = resp.get("json", {}).get("content", "{}")
            parsed = self._json_loads_or_empty(content)
            data = parsed.get("edge_message_content")
            if data is not None:
                _edge_messages_cache[key] = data
            return data

        # Build path with optional point_in_time parameter
        path = f"entity/{entity_id}"
        if point_in_time:
            # Format datetime to ISO 8601 format
            pit_str = point_in_time.isoformat()
            path = f"{path}?pointInTime={pit_str}"

        resp = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service, method="get", path=path
        )

        # Handle 404 responses (entity not found)
        if resp.get("status") == 404:
            return None

        payload = resp.get("json", {})
        if not isinstance(payload, dict):
            return None

        payload_data: Dict[str, Any] = payload.get("data", {}) or {}
        meta_payload = payload.get("meta", {}) or {}
        payload_data["current_state"] = meta_payload.get("state")
        payload_data["technical_id"] = entity_id
        return payload_data

    async def find_all(self, meta: Dict[str, Any]) -> List[Any]:
        """Find all entities of a specific model."""
        path = f"entity/{meta['entity_model']}/{meta['entity_version']}"
        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service, method="get", path=path
        )

        # Handle 404 responses (no entities found)
        if resp.get("status") == 404:
            return []

        json_data = resp.get("json", [])
        return json_data if isinstance(json_data, list) else []

    async def find_all_by_criteria(
        self,
        meta: Dict[str, Any],
        criteria: Any,
        point_in_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Find entities matching specific criteria, optionally at a specific point in time."""
        # Use direct search endpoint: POST /search/{entityName}/{modelVersion}
        search_path = f"search/{meta['entity_model']}/{meta['entity_version']}"

        # Add point_in_time parameter if provided
        if point_in_time:
            pit_str = point_in_time.isoformat()
            search_path = f"{search_path}?pointInTime={pit_str}"

        # Convert criteria to Cyoda-native format if needed
        search_criteria: Dict[str, Any] = self._ensure_cyoda_format(criteria)

        resp = await self._send_search_request(
            method="post", path=search_path, data=json.dumps(search_criteria)
        )

        if resp.get("status") != 200:
            return []

        # Handle the response - it should be a list of entities
        entities_any = resp.get("json", [])
        entities = self._coerce_list_of_dicts(entities_any)
        return self._ensure_technical_id_on_entities(entities)

    # -----------------------
    # Internal HTTP utilities
    # -----------------------

    async def _send_search_request(
        self,
        method: str,
        path: str,
        data: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a search request to the Cyoda API with custom headers and automatic retry on 401.
        Retries once on 401 response by refreshing tokens. Avoids blanket exception catching.
        """
        from common.config.config import CYODA_API_URL
        from common.utils.utils import send_request

        if base_url is None:
            base_url = CYODA_API_URL

        token: str = await self._cyoda_auth_service.get_access_token()

        for attempt in range(2):
            # Prepare headers for search endpoint
            headers: Dict[str, str] = {
                "Content-Type": "application/json",
                "Authorization": (
                    f"Bearer {token}" if not token.startswith("Bearer") else token
                ),
            }

            url = f"{base_url}/{path}"

            # Send request (transport errors bubble up; we only handle 401 responses here)
            response: Dict[str, Any] = await send_request(
                headers, url, method, data=data
            )

            status = response.get("status") if isinstance(response, dict) else None
            if attempt == 0 and status == 401:
                logger.warning(
                    f"Response from {path} returned status 401; invalidating tokens and retrying"
                )
                self._cyoda_auth_service.invalidate_tokens()
                token = await self._cyoda_auth_service.get_access_token()
                continue
            return response

        raise RuntimeError(f"Failed request {method.upper()} {path} after retry")

    # -----------------------
    # Criteria normalization
    # -----------------------

    @staticmethod
    def _ensure_cyoda_format(criteria: Any) -> Dict[str, Any]:
        """Ensure criteria is in Cyoda-native format."""
        if not isinstance(criteria, dict):
            # If it's not a dict, assume it's already acceptable
            return cast(Dict[str, Any], criteria)

        # If it's already in group format, return as-is
        if criteria.get("type") == "group":
            return cast(Dict[str, Any], criteria)

        # If it's a single condition (simple or lifecycle), wrap it in a group
        if criteria.get("type") in ["simple", "lifecycle"]:
            return {"type": "group", "operator": "AND", "conditions": [criteria]}

        # If it's a simple field-value dictionary, convert to Cyoda group format
        conditions: List[Dict[str, Any]] = []
        for field, value in criteria.items():
            if field in ["state", "current_state"]:
                conditions.append(
                    {
                        "type": "lifecycle",
                        "field": field,
                        "operatorType": "EQUALS",
                        "value": value,
                    }
                )
            else:
                # Handle complex field-operator-value format
                if isinstance(value, dict) and len(value) == 1:
                    # Format: {"field": {"operator": "value"}}
                    operator, actual_value = next(iter(value.items()))

                    # Map internal operators back to Cyoda operators
                    operator_mapping: Dict[str, str] = {
                        "eq": "EQUALS",
                        "ieq": "IEQUALS",
                        "ne": "NOT_EQUALS",
                        "contains": "CONTAINS",
                        "icontains": "ICONTAINS",
                        "gt": "GREATER_THAN",
                        "lt": "LESS_THAN",
                        "gte": "GREATER_THAN_OR_EQUAL",
                        "lte": "LESS_THAN_OR_EQUAL",
                        "startswith": "STARTS_WITH",
                        "endswith": "ENDS_WITH",
                        "in": "IN",
                        "not_in": "NOT_IN",
                    }

                    cyoda_operator = operator_mapping.get(str(operator), "EQUALS")

                    # Convert field to jsonPath format
                    json_path = (
                        f"$.{field}" if not str(field).startswith("$.") else str(field)
                    )
                    conditions.append(
                        {
                            "type": "simple",
                            "jsonPath": json_path,
                            "operatorType": cyoda_operator,
                            "value": actual_value,
                        }
                    )
                else:
                    # Simple field-value format: {"field": "value"}
                    json_path = (
                        f"$.{field}" if not str(field).startswith("$.") else str(field)
                    )
                    conditions.append(
                        {
                            "type": "simple",
                            "jsonPath": json_path,
                            "operatorType": "EQUALS",
                            "value": value,
                        }
                    )

        return {"type": "group", "operator": "AND", "conditions": conditions}

    # -----------------------
    # Mutations
    # -----------------------

    async def save(self, meta: Dict[str, Any], entity: Any) -> Optional[str]:
        """Save a single entity."""
        if meta.get("type") == CYODA_ENTITY_TYPE_EDGE_MESSAGE:
            payload: Dict[str, Any] = {
                "meta-data": {"source": "cyoda_client"},
                "payload": {"edge_message_content": entity},
            }
            data = json.dumps(payload, default=custom_serializer)
            path = f"message/new/{meta['entity_model']}_{meta['entity_version']}"
        else:
            data = json.dumps(entity, default=custom_serializer)
            path = f"entity/JSON/{meta['entity_model']}/{meta['entity_version']}"
            logger.info(f"DEBUG: Sending payload to Cyoda: {data}")  # Debug logging

        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="post",
            path=path,
            data=data,
        )
        status = resp.get("status") if isinstance(resp, dict) else None
        if status != 200:
            logger.error(
                "Cyoda save failed: status=%s, body=%s", status, resp.get("json")
            )
        result = resp.get("json", [])
        technical_id = self._extract_technical_id_from_result(result)

        if meta.get("type") == CYODA_ENTITY_TYPE_EDGE_MESSAGE and technical_id:
            _edge_messages_cache[technical_id] = entity

        return technical_id

    async def save_all(
        self, meta: Dict[str, Any], entities: List[Any]
    ) -> Optional[str]:
        """Save multiple entities in batch."""
        data = json.dumps(entities, default=custom_serializer)
        path = f"entity/JSON/{meta['entity_model']}/{meta['entity_version']}"
        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="post",
            path=path,
            data=data,
        )
        result = resp.get("json", [])
        return self._extract_technical_id_from_result(result)

    async def update(
        self, meta: Dict[str, Any], technical_id: Any, entity: Optional[Any] = None
    ) -> Optional[str]:
        """Update an entity or launch a transition."""
        if entity is None:
            # Launch transition returns JSON; no technical id guaranteed
            await self._launch_transition(meta=meta, technical_id=str(technical_id))
            return None

        transition: Optional[str] = meta.get("update_transition")
        if transition:
            path = (
                f"entity/JSON/{technical_id}/{transition}"
                "?transactional=true&waitForConsistencyAfter=true"
            )
        else:
            # Use loopback endpoint (stays in same workflow state) when no transition specified
            path = f"entity/JSON/{technical_id}?transactional=true&waitForConsistencyAfter=true"
        data = json.dumps(entity, default=custom_serializer)
        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service,
            method="put",
            path=path,
            data=data,
        )
        status = resp.get("status") if isinstance(resp, dict) else None
        if status != 200:
            logger.error(
                "Cyoda update failed: status=%s, body=%s", status, resp.get("json")
            )
        result = resp.get("json", {})
        if not isinstance(result, dict):
            logger.exception(result)
            return None
        ids = result.get("entityIds", [None])
        if isinstance(ids, list) and ids and ids[0] is not None:
            return str(ids[0])
        logger.error("Cyoda update returned no entityIds. Body=%s", result)
        return None

    async def delete_by_id(self, meta: Dict[str, Any], technical_id: Any) -> None:
        """Delete entity by ID."""
        path = f"entity/{technical_id}"
        await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service, method="delete", path=path
        )

    async def count(self, meta: Dict[str, Any]) -> int:
        """Count entities of a specific model."""
        items = await self.find_all(meta)
        return len(items)

    async def exists_by_key(self, meta: Dict[str, Any], key: Any) -> bool:
        """Check if entity exists by key."""
        found = await self.find_by_key(meta, key)
        return found is not None

    async def find_by_key(
        self, meta: Dict[str, Any], key: Any
    ) -> Optional[Dict[str, Any]]:
        """Find entity by key."""
        criteria: Dict[str, Any] = cast(
            Dict[str, Any], meta.get("condition") or {"key": key}
        )
        entities = await self.find_all_by_criteria(meta, criteria)
        return entities[0] if entities else None

    async def delete_all(self, meta: Dict[str, Any]) -> None:
        """Delete all entities of a specific model."""
        path = f"entity/{meta['entity_model']}/{meta['entity_version']}"
        await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service, method="delete", path=path
        )

    async def get_meta(
        self, token: str, entity_model: str, entity_version: str
    ) -> Dict[str, Any]:
        """Get metadata for repository operations."""
        return {
            "token": token,
            "entity_model": entity_model,
            "entity_version": entity_version,
        }

    async def _launch_transition(
        self, meta: Dict[str, Any], technical_id: str
    ) -> Dict[str, Any]:
        """Launch entity transition."""
        entity_class: str = (
            EDGE_MESSAGE_CLASS
            if meta.get("type") == CYODA_ENTITY_TYPE_EDGE_MESSAGE
            else TREE_NODE_ENTITY_CLASS
        )
        path = (
            f"platform-api/entity/transition?entityId={technical_id}"
            f"&entityClass={entity_class}&transitionName="
            f"{meta.get('update_transition', UPDATE_TRANSITION)}"
        )
        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service, method="put", path=path
        )
        if resp.get("status") != 200:
            raise Exception(resp.get("json"))
        json_payload = resp.get("json")
        # Ensure a dict is returned for type safety
        return (
            json_payload if isinstance(json_payload, dict) else {"result": json_payload}
        )

    async def get_entity_count(
        self, meta: Dict[str, Any], point_in_time: Optional[datetime] = None
    ) -> int:
        """
        Get count of entities for a specific model, optionally at a point in time.

        Args:
            meta: Metadata containing entity model information
            point_in_time: Optional datetime for temporal queries

        Returns:
            Number of entities
        """
        # Build path for entity statistics endpoint
        path = f"entity/stats/{meta['entity_model']}/{meta['entity_version']}"

        # Add point_in_time parameter if provided
        if point_in_time:
            pit_str = point_in_time.isoformat()
            path = f"{path}?pointInTime={pit_str}"

        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service, method="get", path=path
        )

        if resp.get("status") != 200:
            logger.error(
                "Failed to get entity count: status=%s, body=%s",
                resp.get("status"),
                resp.get("json"),
            )
            return 0

        # Extract count from response
        stats = resp.get("json", {})
        if isinstance(stats, dict):
            return stats.get("count", 0)
        elif isinstance(stats, list) and stats:
            # If response is a list, sum up counts
            total = sum(
                item.get("count", 0) for item in stats if isinstance(item, dict)
            )
            return total

        return 0

    async def get_entity_changes_metadata(
        self, entity_id: Any, point_in_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get entity change history metadata.

        Args:
            entity_id: Unique identifier of the entity
            point_in_time: Optional datetime for temporal queries

        Returns:
            List of change metadata entries
        """
        # Build path for entity changes metadata endpoint
        path = f"entity/{entity_id}/changes"

        # Add point_in_time parameter if provided
        if point_in_time:
            pit_str = point_in_time.isoformat()
            path = f"{path}?pointInTime={pit_str}"

        resp: Dict[str, Any] = await send_cyoda_request(
            cyoda_auth_service=self._cyoda_auth_service, method="get", path=path
        )

        if resp.get("status") != 200:
            logger.error(
                "Failed to get entity changes metadata: status=%s, body=%s",
                resp.get("status"),
                resp.get("json"),
            )
            return []

        # Extract changes from response
        changes = resp.get("json", [])
        if isinstance(changes, list):
            return changes

        return []
