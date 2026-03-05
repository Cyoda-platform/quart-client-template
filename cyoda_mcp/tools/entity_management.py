# ABOUTME: MCP tools for Cyoda entity management operations
# ABOUTME: exposes CRUD, bulk create/update, delete_all, and changes tools

import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import Context, FastMCP

from common.config.config import ENTITY_VERSION
from services.services import get_entity_management_service

# Add the parent directory to the path so we can import from the main app
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Create the MCP server for entity management
mcp = FastMCP("Entity Management")


@mcp.tool
async def get_entity(
    entity_model: str,
    entity_id: str,
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Retrieve a single entity by its technical UUID.

    Use this when you already have the entity UUID (the fastest retrieval
    path). To find an entity by field values use
    `search`; to retrieve every entity of a model use `find_all`.

    Returns `{"success": False, "error": "Entity not found", ...}` when the
    entity does not exist.

    Args:
        entity_model: Name of the entity model (e.g. "laureate", "order").
        entity_id: UUID of the entity to retrieve.
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the entity was found
          - data: entity payload as a JSON object
          - metadata.id: entity UUID
          - metadata.state: current workflow state
          - metadata.entity_type: entity model name
          - metadata.version: model version number
          - metadata.created_at: ISO 8601 creation timestamp
          - metadata.updated_at: ISO 8601 last-update timestamp (None if never updated)
          - metadata.transaction_id: UUID of the last transaction that touched the entity
    """
    if ctx:
        await ctx.info(f"Retrieving {entity_model}:{entity_id}")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.get_entity(
        entity_model, entity_id, entity_version
    )


@mcp.tool
async def create_entity(
    entity_model: str,
    entity_data: Dict[str, Any],
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Create a single new entity and start its workflow.

    The entity is assigned a UUID by the platform, entered into the initial
    workflow state, and its workflow state machine is started. To create many
    entities of the
    same model in one round-trip use `bulk_create_entities`.

    *** The entity model must be in LOCKED state before entities can be saved.
    Use `list_entity_models` to check the model's currentState. ***

    Args:
        entity_model: Name of the entity model (e.g. "laureate", "order").
        entity_data: Payload for the new entity as a JSON-serialisable dict.
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the entity was created
          - entity_id: UUID assigned to the new entity
          - data: entity payload after the saving transaction completes.
          - entity_model: echoed back
          - transaction_id: UUID of the transaction that created the entity
    """
    if ctx:
        await ctx.info(f"Creating {entity_model}")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.create_entity(
        entity_model, entity_data, entity_version
    )


@mcp.tool
async def update_entity_with_loopback_transition(
    entity_model: str,
    entity_id: str,
    entity_data: Dict[str, Any],
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Update an entity's data without changing its workflow state (loopback transition).

    A loopback transition is a virtual transition present on every state that loops back onto the same state, meaning
    that on saving, the state machine engine will try to push the entity forward in workflow, by applying -- if present --
    the first automated transition that is permitted by the criterion guard on that transition. If no such transitions are
    present, the entity stays in the same state (as saved).
    To advance the entity through the workflow with a specific transition, use `update_entity_with_transition`
    instead — call `get_entity_transitions` first to discover valid transition names.

    Args:
        entity_model: Name of the entity model (e.g. "order", "laureate").
        entity_id: UUID of the entity to update.
        entity_data: Full replacement payload for the entity.
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the update was accepted
          - entity_id: UUID of the updated entity
          - data: updated payload after the workflow and saving transaction completes
          - entity_model: echoed back
          - transaction_id: UUID of the transaction that persisted the change
    """
    if ctx:
        await ctx.info(f"Updating {entity_model}:{entity_id} (loopback)")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.update_entity(
        entity_model, entity_id, entity_data, entity_version
    )


@mcp.tool
async def update_entity_with_transition(
    entity_model: str,
    entity_id: str,
    transition: str,
    entity_data: Dict[str, Any],
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Update an entity's data and advance it through an explicit named workflow transition.

    If necessary or unsure, use get_entity_transitions first
    to discover which transitions are valid for the entity's current state. Note that
    the list is a point-in-time snapshot and may be stale by the time this call runs.

    Args:
        entity_model: The type of entity to update (e.g. 'order', 'laureate')
        entity_id: The technical UUID of the entity
        transition: The workflow transition name to apply (required)
        entity_data: The updated data for the entity
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Dictionary with:
          - success: True when the update was accepted
          - entity_id: UUID of the updated entity
          - data: updated payload after the workflow and saving transaction completes
          - entity_model: echoed back
          - transition: transition name that was applied
          - transaction_id: UUID of the transaction that persisted the change
    """
    if ctx:
        await ctx.info(
            f"Updating {entity_model}:{entity_id} via transition '{transition}'"
        )

    entity_management_service = get_entity_management_service()
    return await entity_management_service.update_entity_with_transition(
        entity_model, entity_id, transition, entity_data, entity_version
    )


@mcp.tool
async def get_entity_transitions(
    entity_model: str,
    entity_id: str,
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get the workflow transitions available for an entity at the current moment.

    The result is a point-in-time
    snapshot — the set of valid transitions may change before a subsequent
    update_entity_with_transition call completes.

    Args:
        entity_model: The type of entity (e.g. 'order', 'laureate')
        entity_id: The technical UUID of the entity
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Dictionary with:
          - success: True when the transitions were retrieved
          - transitions: list of valid transition name strings for the current state
          - entity_id: echoed back
          - entity_model: echoed back
    """
    if ctx:
        await ctx.info(f"Getting transitions for {entity_model}:{entity_id}")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.get_entity_transitions(
        entity_model, entity_id, entity_version
    )


@mcp.tool
async def delete_entity(
    entity_model: str,
    entity_id: str,
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Permanently delete a single entity by its UUID.

    Returns `{"success": False, "error": "<reason>", ...}` when the entity
    does not exist or cannot be deleted. *** Deletion is irreversible. ***

    Args:
        entity_model: Name of the entity model (e.g. "laureate", "order").
        entity_id: UUID of the entity to delete.
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the entity was deleted
          - deleted_entity_id: UUID of the deleted entity
          - entity_model: echoed back
    """
    if ctx:
        await ctx.info(f"Deleting {entity_model}:{entity_id}")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.delete_entity(
        entity_model, entity_id, entity_version
    )


@mcp.tool
async def delete_all_entities(
    entity_model: str,
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Permanently delete every entity of a given model in a single operation.

    The deletion is processed in transaction batches (default batch size:
    1 000). The response does not break down partial failures — check `success`
    to confirm the overall outcome.

    *** This operation is irreversible and targets ALL entities of the model.
    Use with extreme caution in production environments. ***

    Args:
        entity_model: Name of the entity model to wipe (e.g. "laureate").
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the API call completed (partial failures possible)
          - entity_model: echoed back
    """
    if ctx:
        await ctx.info(f"Deleting all {entity_model} entities")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.delete_all_entities(
        entity_model, entity_version
    )


@mcp.tool
async def bulk_create_entities(
    entity_model: str,
    entities_data: List[Dict[str, Any]],
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Create multiple entities of the same model in a single round-trip.

    Each entity is assigned a UUID by the platform and its workflow is started.
    Entities are committed in transaction batches (default: 100 per batch,
    default timeout: 10 000 ms per batch).

    *** The entity model must be in LOCKED state. Use `list_entity_models` to
    check the model's currentState before calling this tool. ***

    Args:
        entity_model: Name of the entity model (e.g. "laureate", "order").
        entities_data: List of entity payload dicts — all must conform to the
                       same model schema.
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when all batches were accepted
          - entity_model: echoed back
          - created_count: number of entities submitted
          - response: raw API response [{transactionId, entityIds, success}]
    """
    if ctx:
        await ctx.info(f"Bulk-creating {len(entities_data)} {entity_model} entities")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.bulk_create_entities(
        entity_model, entities_data, entity_version
    )


@mcp.tool
async def bulk_update_entities(
    entity_model: str,
    entities_data: Any,
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Update multiple entities (potentially across different models) in a single call.

    Each update object must have:
      - id: UUID of the entity to update
      - payload: JSON string of the full replacement data
      - transition: workflow transition name to apply (e.g. "UPDATE")

    *** All-or-nothing: if any entity in the list is not found, the entire
    request fails and no entities are updated. ***

    entity_model and entity_version are used for logging context only; the
    actual entity model is determined per-item by the entity ID on the platform.

    Args:
        entity_model: Entity model name for logging purposes only.
        entities_data: List of update objects, each with {id, payload, transition}.
        entity_version: Version for logging purposes only.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when all entities were updated
          - entity_model: echoed back
          - response: raw API response [{transactionId, entityIds, success}]
    """
    if ctx:
        await ctx.info(f"Bulk-updating {entity_model} entities")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.bulk_update_entities(
        entity_model, entities_data, entity_version
    )


@mcp.tool
async def get_entity_changes(
    entity_id: str,
    point_in_time: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Retrieve the change history metadata for a specific entity.

    Returns a chronological list of
    lightweight change records — not the full before/after payloads. For full
    before/after snapshots use `get_entity_audit` with event_type="EntityChange".

    Each change record includes:
      - transactionId: UUID of the transaction that made the change
      - timeOfChange: ISO 8601 timestamp of the change
      - user: identifier of the user who made the change
      - changeType: CREATE, UPDATE, or DELETE
      - fieldsChangedCount: number of fields that changed in this operation

    Args:
        entity_id: UUID of the entity whose change history to retrieve.
        point_in_time: ISO 8601 datetime (e.g. "2026-01-15T00:00:00Z"). When
                       provided, returns the history as it existed at that
                       point in time. Defaults to current system consistency
                       time when omitted.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the API call completed without error
          - entity_id: echoed back
          - changes: list of change metadata records (chronological order)
    """
    if ctx:
        await ctx.info(f"Getting changes for entity {entity_id}")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.get_entity_changes(entity_id, point_in_time)
