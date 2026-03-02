# ABOUTME: MCP tools for Cyoda entity audit log and workflow event queries
# ABOUTME: exposes get_entity_audit_tool and get_workflow_finished_event_tool

import os
import sys
from typing import Any, Dict, Optional

from fastmcp import Context, FastMCP

from services.services import get_entity_audit_service

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

mcp = FastMCP("Entity Audit")


@mcp.tool
async def get_entity_audit_tool(
    entity_id: str,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    from_utc_time: Optional[str] = None,
    to_utc_time: Optional[str] = None,
    transaction_id: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: Optional[int] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Retrieve audit events for an entity from the Cyoda audit log.

    Args:
        entity_id: UUID of the entity
        event_type: Filter by event type (optional)
        severity: Filter by severity level (optional)
        from_utc_time: ISO 8601 start time for time range filter (optional)
        to_utc_time: ISO 8601 end time for time range filter (optional)
        transaction_id: Filter by specific transaction UUID (optional)
        cursor: Pagination cursor from a previous response (optional)
        limit: Maximum number of events to return (optional)
        ctx: FastMCP context for logging

    Returns:
        Dictionary with audit events or error information
    """
    if ctx:
        await ctx.info(f"Fetching audit log for entity {entity_id}")

    service = get_entity_audit_service()
    return await service.get_entity_audit(
        entity_id=entity_id,
        event_type=event_type,
        severity=severity,
        from_utc_time=from_utc_time,
        to_utc_time=to_utc_time,
        transaction_id=transaction_id,
        cursor=cursor,
        limit=limit,
    )


@mcp.tool
async def get_workflow_finished_event_tool(
    entity_id: str,
    transaction_id: str,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Retrieve the workflow finished event for a specific entity transaction.

    Args:
        entity_id: UUID of the entity
        transaction_id: UUID of the workflow transaction
        ctx: FastMCP context for logging

    Returns:
        Dictionary with workflow finished event data or error information
    """
    if ctx:
        await ctx.info(
            f"Fetching workflow finished event for entity {entity_id}, tx {transaction_id}"
        )

    service = get_entity_audit_service()
    return await service.get_workflow_finished_event(entity_id, transaction_id)
