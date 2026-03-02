"""
Edge Message Repository Implementation

Repository for interacting with Cyoda Edge Message API endpoints.
Provides operations for retrieving and sending edge messages.
"""

import json
import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional

from common.config.config import CYODA_API_URL
from common.utils.utils import send_cyoda_request, send_request

logger = logging.getLogger(__name__)


@dataclass
class EdgeMessageHeader:
    """Edge message header information."""

    subject: str
    content_type: str
    content_length: int
    content_encoding: str
    message_id: str
    user_id: str
    recipient: str
    reply_to: str
    correlation_id: str


@dataclass
class EdgeMessageMetadata:
    """Edge message metadata."""

    values: Dict[str, Any]
    indexed_values: Dict[str, Any]


@dataclass
class EdgeMessage:
    """Complete edge message structure."""

    header: EdgeMessageHeader
    metadata: EdgeMessageMetadata
    content: str

    @classmethod
    def from_api_response(cls, response_data: Dict[str, Any]) -> "EdgeMessage":
        """Create EdgeMessage from API response data."""
        header_data = response_data.get("header", {})
        metadata_data = response_data.get("metaData", {})

        header = EdgeMessageHeader(
            subject=header_data.get("subject", ""),
            content_type=header_data.get("contentType", ""),
            content_length=header_data.get("contentLength", 0),
            content_encoding=header_data.get("contentEncoding", ""),
            message_id=header_data.get("messageId", ""),
            user_id=header_data.get("userId", ""),
            recipient=header_data.get("recipient", ""),
            reply_to=header_data.get("replyTo", ""),
            correlation_id=header_data.get("correlationId", ""),
        )

        metadata = EdgeMessageMetadata(
            values=metadata_data.get("values", {}),
            indexed_values=metadata_data.get("indexedValues", {}),
        )

        return cls(
            header=header, metadata=metadata, content=response_data.get("content", "")
        )


@dataclass
class SendMessageResponse:
    """Response from sending a new edge message."""

    entity_ids: list[str]
    success: bool

    @classmethod
    def from_api_response(cls, response_data: Any) -> "SendMessageResponse":
        """Create SendMessageResponse from API response data.

        The Cyoda API returns a list of transaction result objects; take the first entry.
        When the API omits the 'success' field, infer it from the presence of entity IDs.
        """
        if isinstance(response_data, list):
            response_data = response_data[0] if response_data else {}
        entity_ids: list[str] = response_data.get("entityIds", [])
        success: bool = response_data.get("success") or len(entity_ids) > 0
        return cls(entity_ids=entity_ids, success=success)


class EdgeMessageRepository:
    """
    Repository for edge message operations using Cyoda API.
    Thread-safe singleton implementation.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, cyoda_auth_service: Any) -> "EdgeMessageRepository":
        """Thread-safe singleton implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._cyoda_auth_service = cyoda_auth_service  # type: ignore[attr-defined,has-type]
                cls._instance._initialized = False  # type: ignore[attr-defined,has-type]
        return cls._instance

    def __init__(self, cyoda_auth_service: Any) -> None:
        """Initialize the repository."""
        if not self._initialized:  # type: ignore[has-type]
            self._cyoda_auth_service = cyoda_auth_service
            self._initialized = True
            logger.info("EdgeMessageRepository initialized")

    async def _send_cyoda_request_with_headers(
        self,
        method: str,
        path: str,
        data: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        base_url: str = CYODA_API_URL,
    ) -> dict[str, Any]:
        """
        Send an HTTP request to the Cyoda API with custom headers and automatic retry on 401.
        """
        token = await self._cyoda_auth_service.get_access_token()

        for attempt in range(2):
            try:
                # Prepare headers
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": (
                        f"Bearer {token}" if not token.startswith("Bearer") else token
                    ),
                }

                # Add custom headers
                if custom_headers:
                    headers.update(custom_headers)

                url = f"{base_url}/{path}"

                # Send request
                response = await send_request(headers, url, method, data=data)

            except Exception as exc:
                msg = str(exc)
                if attempt == 0 and ("401" in msg or "Unauthorized" in msg):
                    logger.warning(
                        f"Request to {path} failed with 401; invalidating tokens and retrying"
                    )
                    self._cyoda_auth_service.invalidate_tokens()
                    token = await self._cyoda_auth_service.get_access_token()
                    continue
                raise

            status = response.get("status") if isinstance(response, dict) else None
            if attempt == 0 and status == 401:
                logger.warning(
                    f"Response from {path} returned status 401; invalidating tokens and retrying"
                )
                self._cyoda_auth_service.invalidate_tokens()
                token = await self._cyoda_auth_service.get_access_token()
                continue

            return response

        raise RuntimeError(f"Failed request {method.upper()} {path} after retry")

    async def get_message_by_id(self, message_id: str) -> Optional[EdgeMessage]:
        """
        Retrieve an edge message by ID.

        Args:
            message_id: The ID of the message to retrieve

        Returns:
            EdgeMessage object if found, None otherwise

        Raises:
            Exception: If the API request fails
        """
        try:
            path = f"message/{message_id}"

            logger.info(f"Retrieving edge message with ID: {message_id}")

            response = await send_cyoda_request(
                cyoda_auth_service=self._cyoda_auth_service, method="get", path=path
            )

            if response.get("status") != 200:
                logger.warning(f"Failed to retrieve message {message_id}: {response}")
                return None

            # Parse the JSON response
            response_data = response.get("json")
            if not response_data:
                logger.warning(f"No data in response for message {message_id}")
                return None

            # Create EdgeMessage from response
            edge_message = EdgeMessage.from_api_response(response_data)

            logger.info(f"Successfully retrieved edge message {message_id}")
            return edge_message

        except Exception as e:
            logger.exception(f"Error retrieving edge message {message_id}: {e}")
            raise

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
    ) -> SendMessageResponse:
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
            SendMessageResponse with entity IDs and success status

        Raises:
            Exception: If the API request fails
        """
        try:
            path = f"message/new/{subject}"

            # Prepare headers
            headers = {}
            if message_id:
                headers["X-Message-ID"] = message_id
            if user_id:
                headers["X-User-ID"] = user_id
            if recipient:
                headers["X-Recipient"] = recipient
            if reply_to:
                headers["X-Reply-To"] = reply_to
            if correlation_id:
                headers["X-Correlation-ID"] = correlation_id
            if content_encoding:
                headers["Content-Encoding"] = content_encoding

            # Wrap content in payload field per Cyoda API spec
            message_body = {"payload": content}
            content_json = json.dumps(message_body)

            # Content-Length is required per API spec; use computed value unless caller overrides
            headers["Content-Length"] = str(
                content_length or len(content_json.encode("utf-8"))
            )

            logger.info(f"Sending edge message with subject: {subject}")

            response = await self._send_cyoda_request_with_headers(
                method="post", path=path, data=content_json, custom_headers=headers
            )

            if response.get("status") != 200:
                logger.error(f"Failed to send message: {response}")
                raise Exception(f"Failed to send message: {response}")

            # Parse the JSON response
            response_data = response.get("json")
            if not response_data:
                logger.error("No data in send message response")
                raise Exception("No data in send message response")

            # Create SendMessageResponse from response
            send_response = SendMessageResponse.from_api_response(response_data)

            logger.info(
                f"Successfully sent edge message. Entity IDs: {send_response.entity_ids}"
            )
            return send_response

        except Exception as e:
            logger.exception(f"Error sending edge message with subject {subject}: {e}")
            raise

    async def delete_message(self, message_id: str) -> bool:
        """
        Delete a single edge message by ID.

        Args:
            message_id: The UUID of the message to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            path = f"message/{message_id}"
            response = await send_cyoda_request(
                cyoda_auth_service=self._cyoda_auth_service, method="delete", path=path
            )
            success = response.get("status") in (200, 204)
            if not success:
                logger.warning(f"Failed to delete message {message_id}: {response}")
            return success
        except Exception as e:
            logger.exception(f"Error deleting edge message {message_id}: {e}")
            raise

    async def bulk_delete_messages(self, message_ids: list[str]) -> bool:
        """
        Delete multiple edge messages in bulk.

        Args:
            message_ids: List of UUID strings to delete

        Returns:
            True if deletion was accepted, False otherwise
        """
        try:
            data = json.dumps(message_ids)
            response = await self._send_cyoda_request_with_headers(
                method="delete", path="message", data=data
            )
            success = response.get("status") in (200, 204)
            if not success:
                logger.warning(
                    f"Bulk delete failed for {len(message_ids)} messages: {response}"
                )
            return success
        except Exception as e:
            logger.exception(f"Error bulk-deleting edge messages: {e}")
            raise
