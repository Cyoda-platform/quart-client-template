# ABOUTME: MCP tools for Cyoda edge message operations
# ABOUTME: exposes send, get, delete, and bulk-delete edge message tools

import os
import sys
from typing import Any, Dict, List, Optional

from fastmcp import Context, FastMCP

from services.services import get_edge_message_service

# Add the parent directory to the path so we can import from the main app
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


# Create the MCP server for edge message operations
mcp = FastMCP("Edge Message")


@mcp.tool
async def get_edge_message(
    message_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Retrieve a stored edge message by its unique identifier.

    *** message_id MUST be a version 1 (time-based) UUID. The API returns
    HTTP 400 for any other UUID version and HTTP 404 if no message with
    that ID exists. ***

    Response shape (on success):
      - header.subject: routing label the message was sent to
      - header.contentType: MIME type declared at send time
      - header.contentLength: payload size in bytes
      - header.contentEncoding: character encoding (default UTF-8)
      - header.messageId: custom message identifier (if set by sender)
      - header.userId: sender identifier (if set by sender)
      - header.recipient: intended recipient (if set by sender)
      - header.replyTo: reply address (if set by sender)
      - header.correlationId: correlation ID (if set by sender)
      - metaData.values: typed key-value map of non-indexed metadata
      - metaData.indexedValues: typed key-value map of indexed metadata
      - content: raw JSON string of the message payload

    Args:
        message_id: Version 1 (time-based) UUID of the message to retrieve.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the API call completed without error
          - message: EdgeMessageDto body (header, metaData, content fields)
    """
    if ctx:
        await ctx.info(f"Retrieving edge message: {message_id}")

    edge_message_service = get_edge_message_service()
    return await edge_message_service.get_message_by_id(message_id)


@mcp.tool
async def send_edge_message(
    subject: str,
    content: Dict[str, Any],
    message_id: Optional[str] = None,
    user_id: Optional[str] = None,
    recipient: Optional[str] = None,
    reply_to: Optional[str] = None,
    correlation_id: Optional[str] = None,
    content_encoding: Optional[str] = None,
    content_length: Optional[int] = None,
    content_type: str = "application/json",
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Create and store a new edge message routed by subject label.

    subject is a free-form routing key: alphanumeric characters plus `.`, `-`,
    and `_`, maximum 256 characters (e.g. `nobel.prize.events`). The
    interpretation of the subject is entirely application-defined; Cyoda stores
    and routes on it verbatim.

    content must be a JSON object with a required `payload` field (any valid
    JSON value) and an optional `meta-data` object of flat string key-value
    pairs. The meta-data is indexed for fast server-side searching; `payload`
    is stored as a raw JSON blob.

    The tool sets the required `Content-Type` and `Content-Length` HTTP headers
    from the `content_type` parameter and the serialised body length
    respectively. The optional headers (`Content-Encoding`, `X-Message-ID`,
    `X-User-ID`, `X-Recipient`, `X-Reply-To`, `X-Correlation-ID`) are forwarded
    when their corresponding parameters are provided.

    *** Hard size limit: 10 MB. Requests exceeding this limit receive HTTP 413
    and are not stored. ***

    Args:
        subject: Routing label for the message (alphanumeric + `.`, `-`, `_`;
                 max 256 chars).
        content: Message body dict. Must contain a `payload` key (any JSON
                 value). May contain a `meta-data` key with a flat str→str map.
        message_id: Custom message identifier forwarded as X-Message-ID (max
                    1024 chars).
        user_id: Sender identifier forwarded as X-User-ID (max 1024 chars).
        recipient: Intended recipient forwarded as X-Recipient (max 1024 chars).
        reply_to: Reply address forwarded as X-Reply-To (max 1024 chars).
        correlation_id: Correlation token forwarded as X-Correlation-ID (max
                        1024 chars).
        content_encoding: Character encoding forwarded as Content-Encoding
                          (default UTF-8 when omitted).
        content_length: Override for the Content-Length header; computed
                        automatically from the serialised body when omitted.
        content_type: MIME type sent as Content-Type (default application/json).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the message was accepted and stored
          - result: list of [{entityIds: [...], success: bool}] from the API
    """
    if ctx:
        await ctx.info(f"Sending edge message with subject: {subject}")

    edge_message_service = get_edge_message_service()
    return await edge_message_service.send_message(
        subject=subject,
        content=content,
        message_id=message_id,
        user_id=user_id,
        recipient=recipient,
        reply_to=reply_to,
        correlation_id=correlation_id,
        content_encoding=content_encoding,
        content_length=content_length,
        content_type=content_type,
    )


@mcp.tool
async def delete_edge_message(
    message_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Permanently delete a single edge message by its unique identifier.

    *** This operation is irreversible — the message and its associated payload
    blob are removed and cannot be recovered. ***

    *** message_id MUST be a version 1 (time-based) UUID. The API returns
    HTTP 400 for any other UUID version and HTTP 404 if no message with
    that ID exists. ***

    Args:
        message_id: Version 1 (time-based) UUID of the message to delete.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the message was deleted
          - result: {transactionId, entityIds: [...], success: bool} from the API
    """
    if ctx:
        await ctx.info(f"Deleting edge message: {message_id}")

    edge_message_service = get_edge_message_service()
    return await edge_message_service.delete_message(message_id)


@mcp.tool
async def bulk_delete_edge_messages(
    message_ids: List[str], ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Permanently delete multiple edge messages in a single batched request.

    *** This operation is irreversible — all matched messages and their
    associated payload blobs are removed and cannot be recovered. ***

    *** Every ID in message_ids MUST be a version 1 (time-based) UUID. A
    single non-v1 UUID in the list causes HTTP 400 for the entire request;
    no messages are deleted. ***

    Deletion is processed in transaction batches (default batch size: 1 000
    messages per batch). The response contains one entry per batch.

    Args:
        message_ids: List of version 1 (time-based) UUIDs of messages to
                     delete. All IDs must be v1 UUIDs.
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when all batches completed without error
          - result: list of [{transactionId, entityIds: [...], success: bool}],
                    one entry per deletion batch
    """
    if ctx:
        await ctx.info(f"Bulk-deleting {len(message_ids)} edge messages")

    edge_message_service = get_edge_message_service()
    return await edge_message_service.bulk_delete_messages(message_ids)
