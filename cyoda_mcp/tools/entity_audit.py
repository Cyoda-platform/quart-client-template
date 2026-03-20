# ABOUTME: MCP tools for Cyoda entity audit log and workflow event queries
# ABOUTME: exposes get_entity_audit and get_workflow_finished_event tools

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
async def get_entity_audit(
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
    Retrieve audit events for a specific entity from the Cyoda audit log.

    Results are ordered newest-first with cursor-based pagination. The maximum
    searchable period is 180 days; when only one time boundary is supplied the
    API defaults to a 10-day window around it.

    *** RESPONSE SIZE WARNING ***
    Audit logs for active entities can be extremely large. A busy entity may
    accumulate thousands of StateMachine and System events per transaction.
    Always apply the most targeted filters possible before fetching:
      - Prefer `transaction_id` when you care about a single operation.
      - Use `event_type` to restrict to "EntityChange" or "StateMachine" only;
        omit "System" unless doing platform diagnostics — System events are
        excluded by default but add significant volume when requested.
      - Use `from_utc_time` / `to_utc_time` to bound the time window tightly.
      - Set a low `limit` (e.g. 20-50) and paginate via `cursor` rather than
        fetching hundreds of events in one call.

    Event types returned:
      - EntityChange  — data mutations (CREATED / UPDATED / DELETED) with
                        before/after snapshots of the entity payload.
      - StateMachine  — workflow lifecycle steps: STARTED, TRANSITION_MADE,
                        TRANSITION_NOT_FOUND, TRANSITION_CRITERION_NOT_MATCHED,
                        PROCESS_CRITERION_NOT_MATCHED, FINISHED, etc.
      - System        — low-level platform operations (queue, shard, tx
                        processing). High volume; excluded by default.

    Args:
        entity_id: UUID of the entity whose audit trail to query.
        event_type: Comma-separated list of event types to include:
                    "EntityChange", "StateMachine", "System".
                    Defaults to EntityChange + StateMachine (System excluded).
        severity: Filter by severity level: "ERROR", "WARN", "INFO", "DEBUG".
        from_utc_time: ISO 8601 inclusive start of the time window
                       (e.g. "2026-01-15T00:00:00Z"). Defaults to 10 days
                       before to_utc_time when omitted.
        to_utc_time: ISO 8601 exclusive end of the time window.
                     Defaults to 10 days after from_utc_time when omitted.
        transaction_id: UUID of a specific transaction — narrows results to
                        events from that transaction only.
        cursor: Opaque pagination token from `pagination.nextCursor` in a
                previous response. Omit for the first page.
        limit: Maximum events per page (1–1000, default 100). Use a small
               value when the entity is busy or the time window is wide.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - items: list of audit events (see event type descriptions above)
          - pagination.hasNext: True when more pages are available
          - pagination.nextCursor: pass as `cursor` to fetch the next page
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
async def get_workflow_finished_event(
    entity_id: str,
    transaction_id: str,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Retrieve the workflow FINISHED event for a specific entity transaction.

    Use this after a create or update operation to confirm whether the workflow completed
    successfully and which state the entity landed in — without needing to page
    through the full audit log. The `transaction_id` returned by `create_entity`
    or the update tools can be passed directly here.

    *** If either UUID does not exist or the transaction has not yet finished,
    the tool returns `{"success": False, "error": "..."}`. ***

    Response shape (on success):
      - state: workflow state the entity was in when the state machine finished
      - success: True when the workflow execution completed without error
      - stopReason: structured reason the state machine stopped (e.g. FINISHED,
                    TRANSITION_NOT_FOUND, CRITERION_NOT_MATCHED)

    Args:
        entity_id: UUID of the entity.
        transaction_id: UUID of the transaction whose workflow outcome to
                        retrieve.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the event was found
          - event: {state, success, stopReason} from the API
    """
    if ctx:
        await ctx.info(
            f"Fetching workflow finished event for entity {entity_id}, tx {transaction_id}"
        )

    service = get_entity_audit_service()
    return await service.get_workflow_finished_event(entity_id, transaction_id)
