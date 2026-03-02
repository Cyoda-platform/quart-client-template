# ABOUTME: MCP tools for Cyoda async search job lifecycle management
# ABOUTME: exposes submit, status, results, and cancel tools for async search

import os
import sys
from typing import Any, Dict, Optional

from fastmcp import Context, FastMCP

from common.config.config import ENTITY_VERSION
from services.services import get_async_search_service

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

mcp = FastMCP("Async Search")


@mcp.tool
async def submit_async_search_tool(
    entity_model: str,
    condition: Dict[str, Any],
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Submit an async search job for an entity model.
    The condition uses the same format as the synchronous search tool.

    Args:
        entity_model: The entity type to search
        condition: Cyoda search condition (group, simple, or lifecycle format)
        entity_version: The entity model version
        ctx: FastMCP context for logging

    Returns:
        Dictionary with job information including job_id
    """
    if ctx:
        await ctx.info(f"Submitting async search for {entity_model}")

    service = get_async_search_service()
    return await service.submit_async_search(entity_model, condition, entity_version)


@mcp.tool
async def get_async_search_results_tool(
    job_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Retrieve the results of a completed async search job.

    Args:
        job_id: UUID of the async search job (from submit_async_search_tool)
        ctx: FastMCP context for logging

    Returns:
        Dictionary with search results
    """
    if ctx:
        await ctx.info(f"Fetching results for async search job {job_id}")

    service = get_async_search_service()
    return await service.get_async_search_results(job_id)


@mcp.tool
async def get_async_search_status_tool(
    job_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Check the status of a running async search job.

    Args:
        job_id: UUID of the async search job
        ctx: FastMCP context for logging

    Returns:
        Dictionary with current job status
    """
    if ctx:
        await ctx.info(f"Checking status for async search job {job_id}")

    service = get_async_search_service()
    return await service.get_async_search_status(job_id)


@mcp.tool
async def cancel_async_search_tool(
    job_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Cancel a running async search job.

    Args:
        job_id: UUID of the async search job to cancel
        ctx: FastMCP context for logging

    Returns:
        Dictionary with cancellation result
    """
    if ctx:
        await ctx.info(f"Cancelling async search job {job_id}")

    service = get_async_search_service()
    return await service.cancel_async_search(job_id)
