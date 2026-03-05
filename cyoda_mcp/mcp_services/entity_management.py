# ABOUTME: MCP service layer for Cyoda entity management operations
# ABOUTME: wraps EntityService and provides bulk/delete_all/changes support via auth_service

import dataclasses
import json
import logging
from typing import Any, Dict, List, Optional

from common.config.config import ENTITY_VERSION
from common.service.entity_service import EntityService
from common.utils.utils import send_cyoda_request

logger = logging.getLogger(__name__)


class EntityManagementService:
    """Service class for entity management operations."""

    def __init__(self, entity_service: EntityService, auth_service: Any) -> None:
        self.entity_service = entity_service
        self._auth_service = auth_service
        logger.info("EntityManagementService initialized")

    async def get_entity(
        self, entity_model: str, entity_id: str, entity_version: str = ENTITY_VERSION
    ) -> Dict[str, Any]:
        """
        Retrieve a single entity by its technical ID.

        Args:
            entity_model: The type of entity
            entity_id: The technical UUID of the entity
            entity_version: The entity model version

        Returns:
            Dictionary containing entity data or error information
        """
        try:
            if not self.entity_service:
                return {
                    "success": False,
                    "error": "Entity service not available",
                    "entity_id": entity_id,
                    "entity_model": entity_model,
                }

            result = await self.entity_service.get_by_id(
                entity_id, entity_model, entity_version
            )

            if not result:
                return {
                    "success": False,
                    "error": "Entity not found",
                    "entity_id": entity_id,
                    "entity_model": entity_model,
                }

            return {
                "success": True,
                "data": result.data,
                "metadata": dataclasses.asdict(result.metadata),
            }

        except Exception as e:
            logger.exception("get_entity")
            return {
                "success": False,
                "error": str(e),
                "entity_id": entity_id,
                "entity_model": entity_model,
            }

    async def create_entity(
        self,
        entity_model: str,
        entity_data: Dict[str, Any],
        entity_version: str = ENTITY_VERSION,
    ) -> Dict[str, Any]:
        """
        Create a new entity of a given model.

        Args:
            entity_model: The type of entity to create
            entity_data: The data for the new entity
            entity_version: The entity model version

        Returns:
            Dictionary containing created entity information or error
        """
        try:
            if not self.entity_service:
                return {
                    "success": False,
                    "error": "Entity service not available",
                    "entity_model": entity_model,
                }

            result = await self.entity_service.save(
                entity_data, entity_model, entity_version
            )

            return {
                "success": True,
                "entity_id": result.get_id(),
                "data": result.data,
                "entity_model": entity_model,
                "transaction_id": result.metadata.transaction_id,
            }

        except Exception as e:
            logger.exception("create_entity")
            return {
                "success": False,
                "error": str(e),
                "entity_model": entity_model,
                "entity_data": entity_data,
            }

    async def update_entity(
        self,
        entity_model: str,
        entity_id: str,
        entity_data: Dict[str, Any],
        entity_version: str = ENTITY_VERSION,
    ) -> Dict[str, Any]:
        """
        Update an existing entity.

        Args:
            entity_model: The type of entity to update
            entity_id: The technical UUID of the entity
            entity_data: The updated data for the entity
            entity_version: The entity model version

        Returns:
            Dictionary containing updated entity information or error
        """
        try:
            if not self.entity_service:
                return {
                    "success": False,
                    "error": "Entity service not available",
                    "entity_model": entity_model,
                    "entity_id": entity_id,
                }

            result = await self.entity_service.update(
                entity_id, entity_data, entity_model, None, entity_version
            )

            return {
                "success": True,
                "entity_id": result.get_id(),
                "data": result.data,
                "entity_model": entity_model,
                "transaction_id": result.metadata.transaction_id,
            }

        except Exception as e:
            logger.exception("update_entity")
            return {
                "success": False,
                "error": str(e),
                "entity_id": entity_id,
                "entity_model": entity_model,
            }

    async def update_entity_with_transition(
        self,
        entity_model: str,
        entity_id: str,
        transition: str,
        entity_data: Dict[str, Any],
        entity_version: str = ENTITY_VERSION,
    ) -> Dict[str, Any]:
        """Update entity and move it to the next state via an explicit named transition."""
        try:
            if not self.entity_service:
                return {
                    "success": False,
                    "error": "Entity service not available",
                    "entity_model": entity_model,
                    "entity_id": entity_id,
                }

            result = await self.entity_service.update(
                entity_id, entity_data, entity_model, transition, entity_version
            )

            return {
                "success": True,
                "entity_id": result.get_id(),
                "data": result.data,
                "entity_model": entity_model,
                "transition": transition,
                "transaction_id": result.metadata.transaction_id,
            }

        except Exception as e:
            logger.exception("update_entity_with_transition")
            return {
                "success": False,
                "error": str(e),
                "entity_id": entity_id,
                "entity_model": entity_model,
                "transition": transition,
            }

    async def delete_entity(
        self, entity_model: str, entity_id: str, entity_version: str = ENTITY_VERSION
    ) -> Dict[str, Any]:
        """
        Delete an entity by ID.

        Args:
            entity_model: The type of entity to delete
            entity_id: The technical UUID of the entity
            entity_version: The entity model version

        Returns:
            Dictionary containing deletion result or error information
        """
        try:
            if not self.entity_service:
                return {
                    "success": False,
                    "error": "Entity service not available",
                    "entity_model": entity_model,
                    "entity_id": entity_id,
                }

            deleted_id = await self.entity_service.delete_by_id(
                entity_id, entity_model, entity_version
            )

            return {
                "success": True,
                "deleted_entity_id": deleted_id,
                "entity_model": entity_model,
            }

        except Exception as e:
            logger.exception("delete_entity")
            return {
                "success": False,
                "error": str(e),
                "entity_id": entity_id,
                "entity_model": entity_model,
            }

    async def delete_all_entities(
        self, entity_model: str, entity_version: str = ENTITY_VERSION
    ) -> Dict[str, Any]:
        """Delete all entities of a given model via DELETE /entity/{name}/{version}."""
        try:
            path = f"entity/{entity_model}/{entity_version}"
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="delete", path=path
            )
            success = resp.get("status") in (200, 204)
            return {"success": success, "entity_model": entity_model}
        except Exception as e:
            logger.exception("delete_all_entities")
            return {"success": False, "error": str(e), "entity_model": entity_model}

    async def bulk_create_entities(
        self,
        entity_model: str,
        entities_data: List[Dict[str, Any]],
        entity_version: str = ENTITY_VERSION,
    ) -> Dict[str, Any]:
        """Bulk-create entities via POST /entity/JSON/{name}/{version} with a list body."""
        try:
            path = f"entity/JSON/{entity_model}/{entity_version}"
            data = json.dumps(entities_data)
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service,
                method="post",
                path=path,
                data=data,
            )
            success = resp.get("status") == 200
            return {
                "success": success,
                "entity_model": entity_model,
                "created_count": len(entities_data),
                "response": resp.get("json"),
            }
        except Exception as e:
            logger.exception("bulk_create_entities")
            return {"success": False, "error": str(e), "entity_model": entity_model}

    async def bulk_update_entities(
        self,
        entity_model: str,
        entities_data: Any,
        entity_version: str = ENTITY_VERSION,
    ) -> Dict[str, Any]:
        """Bulk-update entities via PUT /entity/JSON with caller-supplied body."""
        try:
            path = "entity/JSON"
            data = json.dumps(entities_data)
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service,
                method="put",
                path=path,
                data=data,
            )
            success = resp.get("status") == 200
            return {
                "success": success,
                "entity_model": entity_model,
                "response": resp.get("json"),
            }
        except Exception as e:
            logger.exception("bulk_update_entities")
            return {"success": False, "error": str(e), "entity_model": entity_model}

    async def get_entity_changes(
        self,
        entity_id: str,
        point_in_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get change history for an entity via GET /entity/{id}/changes."""
        try:
            path = f"entity/{entity_id}/changes"
            if point_in_time:
                path = f"{path}?pointInTime={point_in_time}"
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path=path
            )
            changes = resp.get("json", [])
            if not isinstance(changes, list):
                changes = []
            return {"success": True, "entity_id": entity_id, "changes": changes}
        except Exception as e:
            logger.exception("get_entity_changes")
            return {"success": False, "error": str(e), "entity_id": entity_id}

    async def get_entity_transitions(
        self,
        entity_model: str,
        entity_id: str,
        entity_version: str = ENTITY_VERSION,
    ) -> Dict[str, Any]:
        """Get available workflow transitions for an entity at the current moment.

        This is a point-in-time snapshot; the set of valid transitions may change
        before a subsequent update_entity_with_transition call completes.
        """
        try:
            path = (
                f"platform-api/entity/fetch/transitions"
                f"?entityClass={entity_model}.{entity_version}"
                f"&entityId={entity_id}"
            )
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path=path
            )
            transitions = resp.get("json", [])
            if not isinstance(transitions, list):
                transitions = []
            return {
                "success": True,
                "transitions": transitions,
                "entity_id": entity_id,
                "entity_model": entity_model,
            }
        except Exception as e:
            logger.exception("get_entity_transitions")
            return {
                "success": False,
                "error": str(e),
                "entity_id": entity_id,
                "entity_model": entity_model,
            }
