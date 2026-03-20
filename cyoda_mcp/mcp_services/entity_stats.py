# ABOUTME: MCP service for Cyoda entity statistics endpoints
# ABOUTME: wraps GET /entity/stats and GET /entity/stats/states variants

import logging
from typing import Any, Dict, List, Optional

from common.config.config import ENTITY_VERSION
from common.utils.utils import send_cyoda_request

logger = logging.getLogger(__name__)


class EntityStatsService:
    """Service for entity count and state statistics."""

    def __init__(self, auth_service: Any) -> None:
        self._auth_service = auth_service
        logger.info("EntityStatsService initialized")

    async def get_entity_stats(self) -> Dict[str, Any]:
        """Get aggregate entity statistics across all models via GET /entity/stats."""
        try:
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path="entity/stats"
            )
            return {"success": True, "stats": resp.get("json")}
        except Exception as e:
            logger.exception("get_entity_stats")
            return {"success": False, "error": str(e)}

    async def get_entity_stats_by_model(
        self,
        entity_model: str,
        entity_version: str = ENTITY_VERSION,
        point_in_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get entity count for a specific model via GET /entity/stats/{name}/{version}."""
        try:
            path = f"entity/stats/{entity_model}/{entity_version}"
            if point_in_time:
                path = f"{path}?pointInTime={point_in_time}"
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path=path
            )
            return {
                "success": True,
                "entity_model": entity_model,
                "stats": resp.get("json"),
            }
        except Exception as e:
            logger.exception("get_entity_stats_by_model")
            return {"success": False, "error": str(e), "entity_model": entity_model}

    async def get_entity_stats_by_state(
        self,
        states: Optional[List[str]] = None,
        point_in_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get entity counts grouped by state via GET /entity/stats/states."""
        try:
            params = []
            if states:
                for state in states:
                    params.append(f"states={state}")
            if point_in_time:
                params.append(f"pointInTime={point_in_time}")
            path = "entity/stats/states"
            if params:
                path = f"{path}?{'&'.join(params)}"
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path=path
            )
            return {"success": True, "stats": resp.get("json")}
        except Exception as e:
            logger.exception("get_entity_stats_by_state")
            return {"success": False, "error": str(e)}

    async def get_entity_stats_by_state_and_model(
        self,
        entity_model: str,
        entity_version: str = ENTITY_VERSION,
        states: Optional[List[str]] = None,
        point_in_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get entity counts by state for a model via GET /entity/stats/states/{name}/{version}."""
        try:
            params = []
            if states:
                for state in states:
                    params.append(f"states={state}")
            if point_in_time:
                params.append(f"pointInTime={point_in_time}")
            path = f"entity/stats/states/{entity_model}/{entity_version}"
            if params:
                path = f"{path}?{'&'.join(params)}"
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path=path
            )
            return {
                "success": True,
                "entity_model": entity_model,
                "stats": resp.get("json"),
            }
        except Exception as e:
            logger.exception("get_entity_stats_by_state_and_model")
            return {"success": False, "error": str(e), "entity_model": entity_model}
