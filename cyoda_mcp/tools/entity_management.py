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
    Retrieve a single entity by its technical ID.

    Args:
        entity_model: The type of entity (e.g., 'laureate', 'subscriber', 'job')
        entity_id: The technical UUID of the entity
        entity_version: The entity model version (default: from config)
        ctx: FastMCP context for logging

    Returns:
        The entity data or error information
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
    Create a new entity of a given model.

    Args:
        entity_model: The type of entity to create
        entity_data: The data for the new entity
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Created entity information or error
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

    Calls PUT /entity/JSON/{entityId} with the platform loopback transition so the
    entity remains in its current workflow state. Use this to persist data changes
    when no state progression is needed. To advance the entity through the workflow
    use update_entity_with_transition instead.

    Args:
        entity_model: The type of entity to update (e.g. 'order', 'laureate')
        entity_id: The technical UUID of the entity
        entity_data: The updated data for the entity
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Dictionary with success, entity_id, data, entity_model, transaction_id
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

    Calls PUT /entity/JSON/{entityId}/{transition}. Use get_entity_transitions first
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
        Dictionary with success, entity_id, data, entity_model, transition, transaction_id
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

    Calls GET /platform-api/entity/fetch/transitions. The result is a point-in-time
    snapshot — the set of valid transitions may change before a subsequent
    update_entity_with_transition call completes.

    Args:
        entity_model: The type of entity (e.g. 'order', 'laureate')
        entity_id: The technical UUID of the entity
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Dictionary with success, transitions (list of transition name strings),
        entity_id, entity_model
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
    Delete an entity by ID.

    Args:
        entity_model: The type of entity to delete
        entity_id: The technical UUID of the entity
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Deletion result or error information
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
    Delete all entities of a specific model type.

    Args:
        entity_model: The type of entity (e.g., 'exampleentity')
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Deletion result or error information
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
    Create multiple entities of the same model in a single request.

    Args:
        entity_model: The type of entity to create
        entities_data: List of entity data dictionaries
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Bulk creation result or error information
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
    Bulk-update entities via PUT /entity/JSON.
    The entities_data should be in the format expected by the Cyoda API.

    Args:
        entity_model: The entity model name (used only for logging/context)
        entities_data: Entities to update in Cyoda bulk-update format
        entity_version: The entity model version (used only for logging/context)
        ctx: FastMCP context for logging

    Returns:
        Bulk update result or error information
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
    Get the change history for a specific entity.

    Args:
        entity_id: The technical UUID of the entity
        point_in_time: Optional ISO 8601 datetime to query changes up to that point
        ctx: FastMCP context for logging

    Returns:
        List of change metadata entries or error information
    """
    if ctx:
        await ctx.info(f"Getting changes for entity {entity_id}")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.get_entity_changes(entity_id, point_in_time)
