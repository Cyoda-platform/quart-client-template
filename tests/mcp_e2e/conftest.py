# ABOUTME: pytest configuration and shared fixtures for MCP e2e tests against live Cyoda
# ABOUTME: initializes real Cyoda services and gRPC stream once per session; skips if backend is unreachable

import json
import os
from pathlib import Path

# Must be set before any import that reads GRPC_PROCESSOR_TAG, because
# common.config.config and common.grpc_client.constants evaluate it at
# module-import time.  Using a dedicated tag avoids interfering with other
# calculation nodes that share the same Cyoda backend.
os.environ["GRPC_PROCESSOR_TAG"] = "mcp_test"

import asyncio
import logging

import pytest

from services.config import get_service_config
from services.services import get_auth_service, get_grpc_client, initialize_services, is_initialized, shutdown_services

logger = logging.getLogger(__name__)

_E2E_ENTITY_MODEL = "e2etestentity"
_E2E_ENTITY_VERSION = "1"
_E2E_WORKFLOW_FILE = Path(__file__).parent / "resources" / "workflow" / "E2ETestEntity.json"


@pytest.fixture(scope="session", autouse=True)
async def initialized_services():
    """Initialize real Cyoda services for the entire test session.

    Running as async so that services (and their async HTTP clients) are created
    within the session event loop, preventing cross-loop errors across tests.
    Skips all e2e tests if the backend cannot be reached or credentials are missing.

    Also starts the gRPC stream as a background task so that criterion and processor
    dispatches triggered by workflow transitions are handled by this process, rather
    than spilling onto other clients sharing the mcp_test tag.
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


@pytest.fixture(scope="session", autouse=True)
async def setup_test_entity_model(initialized_services):
    """Ensure E2ETestEntity starts from a clean state with a fresh workflow import.

    Runs once per test session, after services are initialized.
    Steps:
      1. GET /model — check if e2etestentity is already registered.
      2. If it is: delete all its entities, then delete the model itself.
      3. POST /model/e2etestentity/1/workflow/import — register the test workflow.
    """
    from common.utils.utils import send_cyoda_request

    auth_service = get_auth_service()

    resp = await send_cyoda_request(
        cyoda_auth_service=auth_service, method="get", path="model/"
    )
    models = resp.get("json", [])
    if not isinstance(models, list):
        models = []

    model_registered = any(
        str(m.get("name", "")).lower() == _E2E_ENTITY_MODEL for m in models
    )

    if model_registered:
        logger.info("Found existing %s model — cleaning up before tests", _E2E_ENTITY_MODEL)
        await send_cyoda_request(
            cyoda_auth_service=auth_service,
            method="delete",
            path=f"entity/{_E2E_ENTITY_MODEL}/{_E2E_ENTITY_VERSION}",
        )
        await send_cyoda_request(
            cyoda_auth_service=auth_service,
            method="delete",
            path=f"model/{_E2E_ENTITY_MODEL}/{_E2E_ENTITY_VERSION}",
        )

    workflow_def = json.loads(_E2E_WORKFLOW_FILE.read_text(encoding="utf-8"))
    body = json.dumps({"workflows": [workflow_def], "importMode": "REPLACE"})
    await send_cyoda_request(
        cyoda_auth_service=auth_service,
        method="post",
        path=f"model/{_E2E_ENTITY_MODEL}/{_E2E_ENTITY_VERSION}/workflow/import",
        data=body,
    )
    logger.info("E2ETestEntity workflow imported successfully")

