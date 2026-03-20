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
    Retrieve entity counts for every registered model in a single call.

    Use this for a system-wide overview — for example,
    to understand total data volume before deciding which model to query or to
    monitor ingest progress across all models. For counts broken down by workflow
    state use `get_entity_stats_by_state`; for a single model use
    `get_entity_stats_by_model`.

    Returns counts as of the current system consistency time.

    Args:
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on a successful API call
          - stats: list of [{modelName, modelVersion, count}] for each model
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
    Retrieve the total entity count for a specific model.

    Returns `{"success": False, "error": "<reason>", ...}` when the model
    does not exist or the request fails. Supports point-in-time queries for
    historical reporting.

    Args:
        entity_model: Name of the entity model (e.g. "laureate").
        entity_version: Model version string (default from config).
        point_in_time: ISO 8601 datetime (e.g. "2026-01-15T00:00:00Z") for a
                       historical count. Defaults to current system consistency
                       time when omitted.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on a successful API call
          - stats: {modelName, modelVersion, count}
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
    Retrieve entity counts grouped by workflow state across all models.

    Returns one row per (model, state)
    combination. Use this to understand how entities are distributed across
    workflow states system-wide — for example to spot bottlenecks or monitor
    processing pipelines. For a single model use
    `get_entity_stats_by_state_and_model`.

    Args:
        states: Optional list of workflow state names to include (e.g.
                ["PENDING", "VALIDATED"]). When omitted, all current workflow
                states are returned.
        point_in_time: ISO 8601 datetime for a historical snapshot. Defaults
                       to current system consistency time when omitted.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on a successful API call
          - stats: list of [{modelName, modelVersion, state, count}]
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
    Retrieve entity counts grouped by workflow state for a specific model.

    Returns `{"success": False, "error": "<reason>", ...}` when the model
    does not exist or the request fails. Use this to monitor how entities of a
    particular model are distributed across workflow states — for example to
    check how many orders are PENDING vs PAID vs CANCELLED.

    Args:
        entity_model: Name of the entity model (e.g. "laureate", "order").
        entity_version: Model version string (default from config).
        states: Optional list of workflow state names to include. When omitted,
                all current workflow states for the model are returned.
        point_in_time: ISO 8601 datetime for a historical snapshot. Defaults
                       to current system consistency time when omitted.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on a successful API call
          - stats: list of [{modelName, modelVersion, state, count}]
    """
    if ctx:
        await ctx.info(f"Fetching state stats for {entity_model}")

    service = get_entity_stats_service()
    return await service.get_entity_stats_by_state_and_model(
        entity_model, entity_version, states, point_in_time
    )
