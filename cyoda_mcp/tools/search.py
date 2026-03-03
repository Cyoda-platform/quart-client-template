"""
Search MCP Tools

This module provides FastMCP tools for search operations with full Cyoda compliance.
Contains only two tools: find_all and search.
"""

import os
import sys
from typing import Any, Dict, Optional

from fastmcp import Context, FastMCP

from common.config.config import ENTITY_VERSION
from common.service.entity_service import (
    CYODA_OPERATOR_MAPPING,
    LogicalOperator,
    SearchConditionRequest,
    SearchOperator,
)
from services.services import get_entity_service

# Add the parent directory to the path so we can import from the main app
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Create the MCP server for search operations
mcp = FastMCP("Search")


@mcp.tool
async def find_all(
    entity_model: str,
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Retrieve every entity of a given model with no filtering.

    This calls GET /entity/{entityName}/{modelVersion}, which returns all
    entities of the model in a single unfiltered response. There is no
    server-side limit applied — the response size is proportional to the
    total number of entities in the system.

    Use this tool only when you genuinely need the full collection and the
    model is known to be small. For anything else:
      - Use `search` to filter by conditions (synchronous, up to ~1 000
        results by default, 10 000 hard cap).
      - Use `submit_async_search_tool` for large or unknown-size collections.

    Each entity in the result includes:
      - id: UUID of the entity
      - data: the entity payload
      - state: current workflow state
      - created_at / updated_at: timestamps

    Args:
        entity_model: Name of the entity model (e.g. "laureate", "order").
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on success
          - count: number of entities returned
          - entities: list of entity objects (id, data, state, created_at, updated_at)
          - entity_model / entity_version: echoed back
    """
    if ctx:
        await ctx.info(f"Finding all entities of type: {entity_model}")

    try:
        entity_service = get_entity_service()
        if not entity_service:
            return {
                "success": False,
                "error": "Entity service not available",
                "entity_model": entity_model,
            }

        results = await entity_service.find_all(entity_model, entity_version)

        entities = [
            {
                "id": r.get_id(),
                "data": r.data,
                "state": r.metadata.state,
                "created_at": r.metadata.created_at,
                "updated_at": r.metadata.updated_at,
            }
            for r in results
        ]

        return {
            "success": True,
            "count": len(entities),
            "entities": entities,
            "entity_model": entity_model,
            "entity_version": entity_version,
        }

    except Exception as e:
        if ctx:
            await ctx.error(f"Error finding all entities: {str(e)}")
        return {"success": False, "error": str(e), "entity_model": entity_model}


@mcp.tool
async def search(
    entity_model: str,
    search_conditions: Dict[str, Any],
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Perform a synchronous direct search against a Cyoda entity model.

    Executes immediately and returns results in a single response. Best for
    interactive or exploratory queries where the result set is expected to be
    small to medium. The underlying API call is
    POST /search/direct/{entityName}/{modelVersion}.

    Limits and timeouts (applied server-side, not configurable via this tool):
      - Default result limit : 1 000 entities
      - Hard maximum limit   : 10 000 entities (silently truncated if exceeded)
      - Default timeout      : 60 seconds (HTTP 408 returned on timeout)

    If your query might match more than ~1 000 entities, or if the model is
    large and the query broad, use `submit_async_search_tool` instead — it is
    distributed across the cluster and supports full pagination.

    Passing an empty dict {} returns all entities subject to the default limit.

    Condition structure
    -------------------
    Three condition types can be composed into any tree:

    Group — combine sub-conditions with AND / OR:
      {"type": "group", "operator": "AND"|"OR", "conditions": [...]}

    Simple — match entity data using JSONPath:
      {"type": "simple", "jsonPath": "$.field", "operatorType": "<OP>", "value": <v>}

    Lifecycle — match entity metadata (state, creationDate, previousTransition):
      {"type": "lifecycle", "field": "state", "operatorType": "EQUALS", "value": "VALIDATED"}

    Available operatorType values:
      Comparison : EQUALS, NOT_EQUAL, IS_NULL, NOT_NULL,
                   GREATER_THAN, LESS_THAN, GREATER_OR_EQUAL, LESS_OR_EQUAL,
                   BETWEEN, BETWEEN_INCLUSIVE
      String     : CONTAINS, NOT_CONTAINS, STARTS_WITH, NOT_STARTS_WITH,
                   ENDS_WITH, NOT_ENDS_WITH, MATCHES_PATTERN, LIKE
      Case-insens: IEQUALS, INOT_EQUAL, ICONTAINS, INOT_CONTAINS,
                   ISTARTS_WITH, INOT_STARTS_WITH, IENDS_WITH, INOT_ENDS_WITH
      Change     : IS_UNCHANGED, IS_CHANGED

    Example — find married family members born after 1998:
      {
        "type": "group", "operator": "AND", "conditions": [
          {"type": "simple", "jsonPath": "$.married", "operatorType": "EQUALS", "value": true},
          {"type": "simple", "jsonPath": "$.birthdate",
           "operatorType": "GREATER_OR_EQUAL", "value": "1999-01-01"}
        ]
      }

    For backward compatibility, simple field-value pairs are also accepted:
      {"field1": "value1", "field2": "value2"}

    Each entity in the result includes:
      - id: UUID of the entity
      - data: the entity payload
      - state: current workflow state
      - created_at / updated_at: timestamps

    Args:
        entity_model: Name of the entity model to search (e.g. "laureate").
        search_conditions: Cyoda search condition tree (see above).
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on success
          - count: number of entities returned (capped at 10 000)
          - entities: list of matched entity objects
          - search_conditions / entity_model / entity_version: echoed back
    """
    if ctx:
        await ctx.info(
            f"Searching {entity_model} entities with conditions: {search_conditions}"
        )

    try:
        entity_service = get_entity_service()
        if not entity_service:
            return {
                "success": False,
                "error": "Entity service not available",
                "entity_model": entity_model,
            }

        # Build search request from Cyoda conditions
        builder = SearchConditionRequest.builder()

        # Check if this is a Cyoda-style search condition
        if (
            isinstance(search_conditions, dict)
            and search_conditions.get("type") == "group"
        ):
            # Handle complex Cyoda search structure (multiple conditions)
            operator = search_conditions.get("operator", "AND").upper()
            if operator == "AND":
                builder.operator(LogicalOperator.AND)
            elif operator == "OR":
                builder.operator(LogicalOperator.OR)

            conditions = search_conditions.get("conditions", [])
            for condition in conditions:
                _process_cyoda_condition(condition, builder)

        elif isinstance(search_conditions, dict) and search_conditions.get("type") in [
            "simple",
            "lifecycle",
        ]:
            # Handle single Cyoda condition (not wrapped in group)
            _process_cyoda_condition(search_conditions, builder)

        else:
            # Handle simple field-value pairs (backward compatibility)
            for field, value in search_conditions.items():
                builder.equals(field, value)

        search_request = builder.build()
        results = await entity_service.search(
            entity_model, search_request, entity_version
        )

        entities = [
            {
                "id": r.get_id(),
                "data": r.data,
                "state": r.metadata.state,
                "created_at": r.metadata.created_at,
                "updated_at": r.metadata.updated_at,
            }
            for r in results
        ]

        if ctx:
            await ctx.info(
                f"Found {len(entities)} {entity_model} entities matching conditions"
            )

        return {
            "success": True,
            "count": len(entities),
            "entities": entities,
            "search_conditions": search_conditions,
            "entity_model": entity_model,
            "entity_version": entity_version,
        }

    except Exception as e:
        if ctx:
            await ctx.error(f"Error searching entities: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "search_conditions": search_conditions,
            "entity_model": entity_model,
        }


def _process_cyoda_condition(condition: Dict[str, Any], builder: Any) -> None:
    """Process a single Cyoda condition and add it to the builder."""
    condition_type = condition.get("type")

    if condition_type == "lifecycle":
        # Handle lifecycle conditions (entity state)
        field = condition.get("field", "state")
        operator_type = condition.get("operatorType", "EQUALS")
        value = condition.get("value")

        # Map Cyoda operators to internal operators using enum mapping
        search_operator = CYODA_OPERATOR_MAPPING.get(
            operator_type, SearchOperator.EQUALS
        )
        builder.add_condition(field, search_operator, value)

    elif condition_type == "simple":
        # Handle simple JSON path conditions
        json_path = condition.get("jsonPath", "")
        operator_type = condition.get("operatorType", "EQUALS")
        value = condition.get("value")

        # Convert JSON path to field name (remove $. prefix)
        field = json_path.replace("$.", "") if json_path.startswith("$.") else json_path

        # Map Cyoda operators to internal operators using enum mapping
        search_operator = CYODA_OPERATOR_MAPPING.get(
            operator_type, SearchOperator.EQUALS
        )
        builder.add_condition(field, search_operator, value)


# Export the MCP server
__all__ = ["mcp"]
