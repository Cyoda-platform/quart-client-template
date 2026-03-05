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
async def submit_async_search(
    entity_model: str,
    condition: Dict[str, Any],
    entity_version: str = ENTITY_VERSION,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Submit an asynchronous search job against a Cyoda entity model.

    Prefer async search over the synchronous `search` tool when:
      - The result set could exceed ~1 000 entities
      - The query might take longer than 60 seconds
      - You need to retrieve data in multiple pages without holding a connection open

    The job runs in the background across the Cyoda cluster (horizontally
    scalable — query time decreases linearly with cluster size). Poll
    `get_async_search_status` until status is SUCCESSFUL, then retrieve
    pages of results with `get_async_search_results`. To abandon a job
    early use `cancel_async_search`.

    *** Job expiration: jobs are automatically deleted after their expiration
    date (visible in the status response). Retrieve all needed data before
    the job expires — there is no way to restart an expired job. ***

    Passing an empty condition dict {} returns all entities of the model.

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

    Example — find VALIDATED physics Nobel prizes mentioning neural networks:
      {
        "type": "group", "operator": "AND", "conditions": [
          {"type": "lifecycle", "field": "state", "operatorType": "EQUALS", "value": "VALIDATED"},
          {"type": "simple", "jsonPath": "$.category", "operatorType": "EQUALS", "value": "physics"},
          {"type": "simple", "jsonPath": "$.laureates[*].motivation",
           "operatorType": "CONTAINS", "value": "neural networks"}
        ]
      }

    Args:
        entity_model: Name of the entity model to search (e.g. "nobel_prize").
        condition: Search condition tree (group / simple / lifecycle). Pass {}
                   to match all entities.
        entity_version: Model version string (default from config).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True if the job was accepted
          - job_id: UUID string to pass to status / results / cancel tools
          - entity_model: echoed back for reference
    """
    if ctx:
        await ctx.info(f"Submitting async search for {entity_model}")

    service = get_async_search_service()
    return await service.submit_async_search(entity_model, condition, entity_version)


@mcp.tool
async def get_async_search_results(
    job_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Retrieve a page of results from a completed async search job.

    Always call `get_async_search_status` first and confirm the job
    status is SUCCESSFUL before calling this tool. Requesting results while
    the job is still RUNNING will return an empty or partial page.

    Results are sorted in descending order by entity ID. Each item contains:
      - data: the entity payload as a JSON object
      - meta.id: entity UUID
      - meta.state: current workflow state
      - meta.creationDate: ISO 8601 creation timestamp
      - meta.transitionForLatestSave: transition that triggered the last save

    The response also includes pagination metadata:
      - page.totalElements: total number of matched entities
      - page.totalPages: total number of pages
      - page.number: current page index (zero-based)
      - page.size: number of items in this page

    Note: this tool fetches the first page using the API defaults (page 0,
    page size 10). To retrieve subsequent pages or a larger page size,
    call the Cyoda REST API directly at GET /search/async/{jobId}
    with `pageNumber` and `pageSize` query parameters.

    Args:
        job_id: UUID returned by `submit_async_search`.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on a successful API call
          - job_id: echoed back
          - results: paginated response body with `content` and `page` fields
    """
    if ctx:
        await ctx.info(f"Fetching results for async search job {job_id}")

    service = get_async_search_service()
    return await service.get_async_search_results(job_id)


@mcp.tool
async def get_async_search_status(
    job_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Check the current status of an async search job.

    Poll this tool after submitting a job with `submit_async_search`.
    Only fetch results once the status is SUCCESSFUL.

    Possible status values:
      - RUNNING    — job is still executing; poll again after a short delay
      - SUCCESSFUL — job finished; results are ready to page through
      - FAILED     — job encountered an error; results are not available
      - CANCELLED  — job was cancelled via `cancel_async_search`
      - NOT_FOUND  — job does not exist or has expired

    The status response also includes:
      - entitiesCount: number of entities matched so far (updates while RUNNING)
      - expirationDate: when the job and its results will be deleted automatically
      - calculationTimeMillis: elapsed search time in milliseconds
      - createTime: ISO 8601 timestamp when the job was submitted
      - finishTime: ISO 8601 timestamp when the job completed (null if RUNNING)

    Args:
        job_id: UUID returned by `submit_async_search`.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True on a successful API call
          - job_id: echoed back
          - status: response body with searchJobStatus and timing fields
    """
    if ctx:
        await ctx.info(f"Checking status for async search job {job_id}")

    service = get_async_search_service()
    return await service.get_async_search_status(job_id)


@mcp.tool
async def cancel_async_search(
    job_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Request cancellation of a running async search job.

    Cancellation only takes effect when the job is in RUNNING state. If the
    job has already completed (SUCCESSFUL, FAILED) or was previously cancelled,
    `success` is still True — the job is no longer consuming resources
    regardless.

    A successful cancellation invalidates the job entry; subsequent calls to
    `get_async_search_results` or `get_async_search_status` will
    return not-found errors.

    Args:
        job_id: UUID returned by `submit_async_search`.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the API call completed without an unexpected error
          - job_id: echoed back
          - status: outcome code — 200 means the job was cancelled, 400 means
                    it was not in RUNNING state (already finished or cancelled)
    """
    if ctx:
        await ctx.info(f"Cancelling async search job {job_id}")

    service = get_async_search_service()
    return await service.cancel_async_search(job_id)
