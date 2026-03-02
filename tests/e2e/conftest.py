# ABOUTME: pytest configuration and shared fixtures for MCP e2e tests against live Cyoda
# ABOUTME: initializes real Cyoda services and gRPC stream once per session; skips if backend is unreachable

import asyncio
import logging

import pytest

from services.config import get_service_config
from services.services import get_grpc_client, initialize_services, is_initialized, shutdown_services

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
async def initialized_services():
    """Initialize real Cyoda services for the entire test session.

    Running as async so that services (and their async HTTP clients) are created
    within the session event loop, preventing cross-loop errors across tests.
    Skips all e2e tests if the backend cannot be reached or credentials are missing.

    Also starts the gRPC stream as a background task so that criterion and processor
    dispatches triggered by workflow transitions are handled by this process, rather
    than spilling onto other clients sharing the same cyoda_application tag.
    """
    if not is_initialized():
        try:
            config = get_service_config()
            initialize_services(config)
        except Exception as exc:
            pytest.skip(f"Cyoda backend not available - skipping e2e tests: {exc}")

    grpc_client = get_grpc_client()
    grpc_task = asyncio.create_task(grpc_client.grpc_stream())

    yield

    grpc_client.stop()
    try:
        await asyncio.wait_for(grpc_task, timeout=5.0)
    except asyncio.TimeoutError:
        grpc_task.cancel()
        try:
            await grpc_task
        except asyncio.CancelledError:
            pass

    shutdown_services()

