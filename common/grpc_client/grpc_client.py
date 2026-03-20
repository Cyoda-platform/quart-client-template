"""
Simple, dull GrpcClient for backward compatibility.
All complex logic has been moved to factory.py and legacy_methods.py.
"""

import logging
from typing import Any, Optional

# Import constants for backward compatibility
from common.grpc_client.constants import (
    CALC_REQ_EVENT_TYPE,
    CALC_RESP_EVENT_TYPE,
    CRITERIA_CALC_REQ_EVENT_TYPE,
    CRITERIA_CALC_RESP_EVENT_TYPE,
    ERROR_EVENT_TYPE,
    EVENT_ACK_TYPE,
    GREET_EVENT_TYPE,
    JOIN_EVENT_TYPE,
    KEEP_ALIVE_EVENT_TYPE,
    OWNER,
    SOURCE,
    SPEC_VERSION,
    TAGS,
)
from common.utils.event_loop import BackgroundEventLoop

logger = logging.getLogger(__name__)


class GrpcClient:
    """
    Dull wrapper class for backward compatibility.
    All logic moved elsewhere - this just delegates.
    """

    def __init__(self, auth: Any) -> None:
        # Store dependencies
        self.auth = auth
        self.processor_loop = BackgroundEventLoop()

        # Lazy initialization
        self._facade: Optional[Any] = None

    def _get_facade(self) -> Any:
        """Get facade, creating it if needed."""
        if self._facade is None:
            from common.grpc_client.factory import GrpcStreamingFacadeFactory

            self._facade = GrpcStreamingFacadeFactory.create(
                auth=self.auth, processor_loop=self.processor_loop, grpc_client=self
            )
        return self._facade

    # Main entry points - simple delegation
    async def grpc_stream(self) -> None:
        """Entry point."""
        try:
            await self._get_facade().start()
        except Exception as e:
            logger.exception(e)

    def stop(self) -> None:
        """Stop the gRPC streaming connection."""
        self._get_facade().stop()


# Re-export constants for backward compatibility
__all__ = [
    "GrpcClient",
    "TAGS",
    "OWNER",
    "SPEC_VERSION",
    "SOURCE",
    "JOIN_EVENT_TYPE",
    "CALC_RESP_EVENT_TYPE",
    "CALC_REQ_EVENT_TYPE",
    "CRITERIA_CALC_REQ_EVENT_TYPE",
    "CRITERIA_CALC_RESP_EVENT_TYPE",
    "GREET_EVENT_TYPE",
    "KEEP_ALIVE_EVENT_TYPE",
    "EVENT_ACK_TYPE",
    "ERROR_EVENT_TYPE",
]
