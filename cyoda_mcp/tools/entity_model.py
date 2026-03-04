# ABOUTME: MCP tool for discovering Cyoda entity models via GET /model/
# ABOUTME: enables AI assistants to list available entity types before operating on them

import os
import sys
from typing import Any, Dict, Optional

from fastmcp import Context, FastMCP

from services.services import get_entity_model_service

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

mcp = FastMCP("Entity Model")


@mcp.tool
async def list_entity_models(ctx: Optional[Context] = None) -> Dict[str, Any]:
    """
    List all entity models registered in the Cyoda environment.
    Use this before performing entity operations to discover available entity types.

    Args:
        ctx: FastMCP context for logging

    Returns:
        Dictionary with 'models' list and 'count'
    """
    if ctx:
        await ctx.info("Listing all entity models")

    service = get_entity_model_service()
    return await service.list_entity_models()
