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

    *** If the message_id does not exist, the tool returns `{"success": False,
    "error": "..."}`. ***

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
            (contains the `metadata` key-value pairs passed at send time)
      - content: raw JSON string of the message payload

    Args:
        message_id: UUID of the message to retrieve (assigned by Cyoda on send).
        ctx: FastMCP context for logging.

    Returns:
        Dictionary with:
          - success: True when the API call completed without error
          - message: EdgeMessageDto body (header, metaData, content fields)
          - message_id: echoed back
    """
    if ctx:
        await ctx.info(f"Retrieving edge message: {message_id}")

    edge_message_service = get_edge_message_service()
    return await edge_message_service.get_message_by_id(message_id)


@mcp.tool
async def send_edge_message(
    subject: str,
    content: Dict[str, Any],
    metadata: Optional[Dict[str, str]] = None,
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

    content is the message payload — any valid JSON object. It is stored as a
    raw JSON blob under the `payload` field of the Cyoda message body.

    metadata is an optional flat string→string map stored alongside the payload
    under the `meta-data` field. These key-value pairs are indexed server-side
    for fast searching. Use metadata to attach routing, classification, or
    chunking information without altering the payload itself.

    *** Hard size limit: 10 MB per message. Payloads exceeding this limit are
    rejected and the tool returns `{"success": False, "error": "..."}`.
    For payloads larger than 10 MB, split the data into chunks and send each
    chunk as a separate message. Use `correlation_id` to group the chunks and
    `metadata` to record sequencing information (e.g. `{"chunkIndex": "0",
    "totalChunks": "3"}`), then reassemble on the reader side by fetching all
    messages with the same correlation ID. ***

    Args:
        subject: Routing label for the message (alphanumeric + `.`, `-`, `_`;
                 max 256 chars).
        content: Payload data as a JSON-serialisable dict (any structure).
        metadata: Optional flat str→str map of indexed key-value pairs stored
                  as `meta-data` alongside the payload. Useful, for example, for search,
                  classification, and chunked-message sequencing.
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
          - entity_ids: list of UUIDs assigned to the stored message(s)
          - subject: echoed back
          - message_id: echoed back (None if not provided)
          - correlation_id: echoed back (None if not provided)
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
        metadata=metadata,
    )


@mcp.tool
async def delete_edge_message(
    message_id: str, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Permanently delete a single edge message by its unique identifier.

    *** This operation is irreversible — the message and its associated payload
    blob are removed and cannot be recovered. ***

    *** If the message_id does not exist, the tool returns `{"success": False,
    "error": "..."}`. ***

    Args:
        message_id: UUID of the message to delete (assigned by Cyoda on send).
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

    *** If any ID does not exist, the entire request fails (`success: False`);
    no messages are deleted. ***

    Deletion is processed in transaction batches (default batch size: 1 000
    messages per batch). The response contains one entry per batch.

    Args:
        message_ids: List of message UUIDs to delete (assigned by Cyoda on
                     send).
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
