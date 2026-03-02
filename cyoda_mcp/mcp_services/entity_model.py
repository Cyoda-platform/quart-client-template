# ABOUTME: MCP service for listing Cyoda entity models via GET /model/
# ABOUTME: enables AI assistants to discover available entity types

import logging
from typing import Any, Dict

from common.utils.utils import send_cyoda_request

logger = logging.getLogger(__name__)


class EntityModelService:
    """Service for entity model discovery."""

    def __init__(self, auth_service: Any) -> None:
        self._auth_service = auth_service
        logger.info("EntityModelService initialized")

    async def list_entity_models(self) -> Dict[str, Any]:
        """
        List all registered entity models via GET /model/.

        Returns:
            Dictionary with success flag and list of models
        """
        try:
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path="model/"
            )
            models = resp.get("json")
            if not isinstance(models, list):
                models = [models] if models else []
            return {"success": True, "models": models, "count": len(models)}
        except Exception as e:
            logger.exception("list_entity_models")
            return {"success": False, "error": str(e)}
