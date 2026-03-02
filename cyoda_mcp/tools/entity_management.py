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
async def get_entity_tool(
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
async def list_entities_tool(
    entity_model: str, entity_version: str = ENTITY_VERSION
) -> Dict[str, Any]:
    """
    List all entities of a specific type.

    Args:
        entity_model: The type of entity to list
        entity_version: The entity model version

    Returns:
        List of entities or error information
    """
    entity_management_service = get_entity_management_service()
    return await entity_management_service.list_entities(entity_model, entity_version)


@mcp.tool
async def create_entity_tool(
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
async def update_entity_tool(
    entity_model: str,
    entity_id: str,
    entity_data: Dict[str, Any],
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Update an existing entity.

    Args:
        entity_model: The type of entity to update
        entity_id: The technical UUID of the entity
        entity_data: The updated data for the entity
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Updated entity information or error
    """
    if ctx:
        await ctx.info(f"Updating {entity_model}:{entity_id}")

    entity_management_service = get_entity_management_service()
    return await entity_management_service.update_entity(
        entity_model, entity_id, entity_data, entity_version
    )


@mcp.tool
async def delete_entity_tool(
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
async def delete_all_entities_tool(
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
async def bulk_create_entities_tool(
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
async def bulk_update_entities_tool(
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
async def get_entity_changes_tool(
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
