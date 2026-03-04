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
    Retrieve an edge message by ID.

    Args:
        message_id: The ID of the message to retrieve
        ctx: FastMCP context for logging

    Returns:
        Dictionary containing message data or error information
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
    Send a new edge message.

    Args:
        subject: Message subject
        content: Message content as dictionary
        message_id: Optional message ID
        user_id: Optional user ID
        recipient: Optional recipient
        reply_to: Optional reply-to address
        correlation_id: Optional correlation ID
        content_encoding: Optional content encoding
        content_length: Optional content length
        content_type: Content type (default: application/json)
        ctx: FastMCP context for logging

    Returns:
        Dictionary containing send result or error information
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
    Delete a single edge message by ID.

    Args:
        message_id: The UUID of the message to delete
        ctx: FastMCP context for logging

    Returns:
        Dictionary with success status
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
    Delete multiple edge messages in a single request.

    Args:
        message_ids: List of message UUIDs to delete
        ctx: FastMCP context for logging

    Returns:
        Dictionary with success status and count
    """
    if ctx:
        await ctx.info(f"Bulk-deleting {len(message_ids)} edge messages")

    edge_message_service = get_edge_message_service()
    return await edge_message_service.bulk_delete_messages(message_ids)
