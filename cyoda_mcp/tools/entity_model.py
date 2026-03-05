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

    Call this first when you do not yet know the available
    entity model names or their current states. The response is the authoritative
    list — no filtering or paging is applied.

    Each model entry includes:
      - id: UUID of the model definition
      - modelName: the name to pass as entity_model to other tools
      - modelVersion: version integer to pass as entity_version
      - currentState: LOCKED (entities can be written) or UNLOCKED (model can
                      be modified but entity writes are disabled)
      - modelUpdateDate: ISO 8601 timestamp of the last schema change

    *** Only LOCKED models accept entity create/update operations. ***

    Args:
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on a successful API call
          - models: list of model descriptor objects (see above)
          - count: total number of registered models
    """
    if ctx:
        await ctx.info("Listing all entity models")

    service = get_entity_model_service()
    return await service.list_entity_models()
