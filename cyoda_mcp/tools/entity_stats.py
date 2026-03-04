# ABOUTME: MCP tools for querying Cyoda entity statistics
# ABOUTME: exposes global stats, per-model stats, and state-grouped stats tools

import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import Context, FastMCP

from common.config.config import ENTITY_VERSION
from services.services import get_entity_stats_service

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

mcp = FastMCP("Entity Stats")


@mcp.tool
async def get_entity_stats(ctx: Optional[Context] = None) -> Dict[str, Any]:
    """
    Get aggregate entity statistics across all models in Cyoda.

    Args:
        ctx: FastMCP context for logging

    Returns:
        Dictionary with entity statistics
    """
    if ctx:
        await ctx.info("Fetching global entity statistics")

    service = get_entity_stats_service()
    return await service.get_entity_stats()


@mcp.tool
async def get_entity_stats_by_model(
    entity_model: str,
    entity_version: str = ENTITY_VERSION,
    point_in_time: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get entity count statistics for a specific entity model.

    Args:
        entity_model: The entity type name
        entity_version: The entity model version
        point_in_time: Optional ISO 8601 datetime for historical queries
        ctx: FastMCP context for logging

    Returns:
        Dictionary with statistics for the given model
    """
    if ctx:
        await ctx.info(f"Fetching stats for {entity_model}")

    service = get_entity_stats_service()
    return await service.get_entity_stats_by_model(
        entity_model, entity_version, point_in_time
    )


@mcp.tool
async def get_entity_stats_by_state(
    states: Optional[List[str]] = None,
    point_in_time: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get entity counts grouped by workflow state across all models.

    Args:
        states: Optional list of states to filter by
        point_in_time: Optional ISO 8601 datetime for historical queries
        ctx: FastMCP context for logging

    Returns:
        Dictionary with per-state entity counts
    """
    if ctx:
        await ctx.info("Fetching entity stats grouped by state")

    service = get_entity_stats_service()
    return await service.get_entity_stats_by_state(states, point_in_time)


@mcp.tool
async def get_entity_stats_by_state_and_model(
    entity_model: str,
    entity_version: str = ENTITY_VERSION,
    states: Optional[List[str]] = None,
    point_in_time: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Get entity counts grouped by workflow state for a specific model.

    Args:
        entity_model: The entity type name
        entity_version: The entity model version
        states: Optional list of states to filter by
        point_in_time: Optional ISO 8601 datetime for historical queries
        ctx: FastMCP context for logging

    Returns:
        Dictionary with per-state entity counts for the model
    """
    if ctx:
        await ctx.info(f"Fetching state stats for {entity_model}")

    service = get_entity_stats_service()
    return await service.get_entity_stats_by_state_and_model(
        entity_model, entity_version, states, point_in_time
    )
