"""
Edge Message Service for MCP

This service provides edge message functionality for the MCP server,
using the EdgeMessageRepository for Cyoda API operations.
"""

import logging
from typing import Any, Dict, List, Optional

from common.repository.cyoda.edge_message_repository import EdgeMessageRepository

logger = logging.getLogger(__name__)


class EdgeMessageService:
    """Service class for edge message operations."""

    def __init__(self, edge_message_repository: EdgeMessageRepository):
        """
        Initialize the edge message service.

        Args:
            edge_message_repository: The injected edge message repository
        """
        self.edge_message_repository = edge_message_repository
        logger.info("EdgeMessageService initialized")

    async def get_message_by_id(self, message_id: str) -> Dict[str, Any]:
        """
        Retrieve an edge message by ID.

        Args:
            message_id: The ID of the message to retrieve

        Returns:
            Dictionary containing message data or error information
        """
        try:
            if not self.edge_message_repository:
                return {
                    "success": False,
                    "error": "Edge message repository not available",
                    "message_id": message_id,
                }

            message = await self.edge_message_repository.get_message_by_id(message_id)

            if not message:
                return {
                    "success": False,
                    "error": "Message not found",
                    "message_id": message_id,
                }

            # Convert message to dictionary format
            message_data = {
                "header": {
                    "subject": message.header.subject,
                    "contentType": message.header.content_type,
                    "contentLength": message.header.content_length,
                    "contentEncoding": message.header.content_encoding,
                    "messageId": message.header.message_id,
                    "userId": message.header.user_id,
                    "recipient": message.header.recipient,
                    "replyTo": message.header.reply_to,
                    "correlationId": message.header.correlation_id,
                },
                "metaData": {
                    "values": message.metadata.values,
                    "indexedValues": message.metadata.indexed_values,
                },
                "content": message.content,
            }

            logger.info(f"Successfully retrieved edge message {message_id}")

            return {"success": True, "message": message_data, "message_id": message_id}

        except Exception as e:
            logger.exception(f"Failed to retrieve edge message {message_id}: {e}")
            return {"success": False, "error": str(e), "message_id": message_id}

    async def send_message(
        self,
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

        Returns:
            Dictionary containing send result or error information
        """
        try:
            if not self.edge_message_repository:
                return {
                    "success": False,
                    "error": "Edge message repository not available",
                    "subject": subject,
                }

            response = await self.edge_message_repository.send_message(
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

            logger.info(f"Successfully sent edge message with subject {subject}")

            return {
                "success": response.success,
                "entity_ids": response.entity_ids,
                "subject": subject,
                "message_id": message_id,
                "user_id": user_id,
                "recipient": recipient,
                "correlation_id": correlation_id,
            }

        except Exception as e:
            logger.exception(f"Failed to send edge message with subject {subject}: {e}")
            return {"success": False, "error": str(e), "subject": subject}

    async def send_nobel_prize_message(
        self,
        category: str,
        year: str,
        laureates: List[Dict[str, Any]],
        message_id: Optional[str] = None,
        user_id: str = "nobel-committee",
        recipient: str = "scientific-community",
        reply_to: str = "announcements@nobelprize.org",
    ) -> Dict[str, Any]:
        """
        Send a Nobel Prize announcement message (convenience method).

        Args:
            category: Prize category (e.g., "physics", "chemistry")
            year: Prize year
            laureates: List of laureate information
            message_id: Optional message ID
            user_id: User ID (default: "nobel-committee")
            recipient: Recipient (default: "scientific-community")
            reply_to: Reply-to address (default: "announcements@nobelprize.org")

        Returns:
            Dictionary containing send result or error information
        """
        try:
            # Build Nobel Prize content
            content = {
                "eventType": "nobel.prize.announced",
                "timestamp": "2024-10-09T12:00:00Z",  # Could be made dynamic
                "data": {"category": category, "year": year, "laureates": laureates},
            }

            # Generate correlation ID if not provided
            correlation_id = f"nobel-{year}-{category}-announcement"

            # Generate message ID if not provided
            if not message_id:
                message_id = f"msg-nobel-{year}-{category}"

            return await self.send_message(
                subject="nobel.prize.events",
                content=content,
                message_id=message_id,
                user_id=user_id,
                recipient=recipient,
                reply_to=reply_to,
                correlation_id=correlation_id,
            )

        except Exception as e:
            logger.exception(
                f"Failed to send Nobel Prize message for {category} {year}: {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "category": category,
                "year": year,
            }

    async def send_custom_event_message(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        subject: str,
        message_id: Optional[str] = None,
        user_id: Optional[str] = None,
        recipient: Optional[str] = None,
        reply_to: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a custom event message (convenience method).

        Args:
            event_type: Type of event
            event_data: Event data
            subject: Message subject
            message_id: Optional message ID
            user_id: Optional user ID
            recipient: Optional recipient
            reply_to: Optional reply-to address
            correlation_id: Optional correlation ID

        Returns:
            Dictionary containing send result or error information
        """
        try:
            # Build custom event content
            content = {
                "eventType": event_type,
                "timestamp": "2024-10-09T12:00:00Z",  # Could be made dynamic
                "data": event_data,
            }

            return await self.send_message(
                subject=subject,
                content=content,
                message_id=message_id,
                user_id=user_id,
                recipient=recipient,
                reply_to=reply_to,
                correlation_id=correlation_id,
            )

        except Exception as e:
            logger.exception(f"Failed to send custom event message {event_type}: {e}")
            return {
                "success": False,
                "error": str(e),
                "event_type": event_type,
                "subject": subject,
            }

    async def delete_message(self, message_id: str) -> Dict[str, Any]:
        """Delete a single edge message by ID."""
        try:
            success = await self.edge_message_repository.delete_message(message_id)
            return {"success": success, "message_id": message_id}
        except Exception as e:
            logger.exception(f"Failed to delete edge message {message_id}: {e}")
            return {"success": False, "error": str(e), "message_id": message_id}

    async def bulk_delete_messages(self, message_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple edge messages in bulk."""
        try:
            success = await self.edge_message_repository.bulk_delete_messages(
                message_ids
            )
            return {"success": success, "deleted_count": len(message_ids)}
        except Exception as e:
            logger.exception(f"Failed to bulk-delete edge messages: {e}")
            return {"success": False, "error": str(e), "message_ids": message_ids}
