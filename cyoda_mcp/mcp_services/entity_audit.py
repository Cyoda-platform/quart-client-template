# ABOUTME: MCP service for Cyoda entity audit and workflow event queries
# ABOUTME: wraps GET /audit/entity and GET /audit/entity/.../workflow endpoints

import logging
from typing import Any, Dict, Optional

from common.utils.utils import send_cyoda_request

logger = logging.getLogger(__name__)


class EntityAuditService:
    """Service for entity audit log and workflow finished event queries."""

    def __init__(self, auth_service: Any) -> None:
        self._auth_service = auth_service
        logger.info("EntityAuditService initialized")

    async def get_entity_audit(
        self,
        entity_id: str,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        from_utc_time: Optional[str] = None,
        to_utc_time: Optional[str] = None,
        transaction_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve audit events for an entity via GET /audit/entity/{entityId}.

        Args:
            entity_id: UUID of the entity
            event_type: Optional filter by event type
            severity: Optional filter by severity
            from_utc_time: Optional ISO 8601 start time
            to_utc_time: Optional ISO 8601 end time
            transaction_id: Optional transaction UUID filter
            cursor: Optional pagination cursor
            limit: Optional result limit
        """
        try:
            params = []
            if event_type:
                params.append(f"eventType={event_type}")
            if severity:
                params.append(f"severity={severity}")
            if from_utc_time:
                params.append(f"fromUtcTime={from_utc_time}")
            if to_utc_time:
                params.append(f"toUtcTime={to_utc_time}")
            if transaction_id:
                params.append(f"transactionId={transaction_id}")
            if cursor:
                params.append(f"cursor={cursor}")
            if limit is not None:
                params.append(f"limit={limit}")

            path = f"audit/entity/{entity_id}"
            if params:
                path = f"{path}?{'&'.join(params)}"

            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path=path
            )
            return {"success": True, "entity_id": entity_id, "audit": resp.get("json")}
        except Exception as e:
            logger.exception("get_entity_audit")
            return {"success": False, "error": str(e), "entity_id": entity_id}

    async def get_workflow_finished_event(
        self, entity_id: str, transaction_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve the workflow finished event for a specific transaction.

        Args:
            entity_id: UUID of the entity
            transaction_id: UUID of the workflow transaction
        """
        try:
            path = f"audit/entity/{entity_id}/workflow/{transaction_id}/finished"
            resp = await send_cyoda_request(
                cyoda_auth_service=self._auth_service, method="get", path=path
            )
            return {
                "success": True,
                "entity_id": entity_id,
                "transaction_id": transaction_id,
                "event": resp.get("json"),
            }
        except Exception as e:
            logger.exception("get_workflow_finished_event")
            return {
                "success": False,
                "error": str(e),
                "entity_id": entity_id,
                "transaction_id": transaction_id,
            }
