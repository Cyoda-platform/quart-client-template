# ABOUTME: MCP service for Cyoda async search operations
# ABOUTME: wraps POST /search/async and GET/PUT /search/async/{jobId} endpoints

import json
import logging
from typing import Any, Dict

from common.config.config import ENTITY_VERSION
from common.utils.utils import send_cyoda_request

logger = logging.getLogger(__name__)


class AsyncSearchService:
    """Service for submitting and managing async entity search jobs."""

    def __init__(self, auth_service: Any) -> None:
        self._auth_service = auth_service
        logger.info("AsyncSearchService initialized")

    async def submit_async_search(
        self,
        entity_model: str,
        condition: Dict[str, Any],
        entity_version: str = ENTITY_VERSION,
    ) -> Dict[str, Any]:
        """
        Submit an async search job via POST /search/async/{name}/{version}.

        Args:
            entity_model: Entity type to search
            condition: Cyoda search condition (same format as sync search)
            entity_version: Entity model version
        """
        try:
            path = f"search/async/{entity_model}/{entity_version}"
            data = json.dumps(condition)
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service,
                method="post",
                path=path,
                data=data,
            )
            # Cyoda returns the job_id as a plain UUID string in the response body
            job_id = resp.get("json")
            return {
                "success": resp.get("status") == 200,
                "entity_model": entity_model,
                "job_id": job_id if isinstance(job_id, str) else None,
                "job": job_id,
            }
        except Exception as e:
            logger.exception("submit_async_search")
            return {"success": False, "error": str(e), "entity_model": entity_model}

    async def get_async_search_results(self, job_id: str) -> Dict[str, Any]:
        """
        Retrieve results for a completed async search job via GET /search/async/{jobId}.

        Args:
            job_id: UUID of the async search job
        """
        try:
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service,
                method="get",
                path=f"search/async/{job_id}",
            )
            return {"success": True, "job_id": job_id, "results": resp.get("json")}
        except Exception as e:
            logger.exception("get_async_search_results")
            return {"success": False, "error": str(e), "job_id": job_id}

    async def get_async_search_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check the status of an async search job via GET /search/async/{jobId}/status.

        Args:
            job_id: UUID of the async search job
        """
        try:
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service,
                method="get",
                path=f"search/async/{job_id}/status",
            )
            return {"success": True, "job_id": job_id, "status": resp.get("json")}
        except Exception as e:
            logger.exception("get_async_search_status")
            return {"success": False, "error": str(e), "job_id": job_id}

    async def cancel_async_search(self, job_id: str) -> Dict[str, Any]:
        """
        Cancel a running async search job via PUT /search/async/{jobId}/cancel.

        Args:
            job_id: UUID of the async search job to cancel
        """
        try:
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service,
                method="put",
                path=f"search/async/{job_id}/cancel",
            )
            status = resp.get("status")
            # 200 = cancelled; 400 = job already finished (not an error from the caller's perspective)
            success = status in (200, 204, 400)
            return {"success": success, "job_id": job_id, "status": status}
        except Exception as e:
            logger.exception("cancel_async_search")
            return {"success": False, "error": str(e), "job_id": job_id}
