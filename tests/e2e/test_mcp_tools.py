# ABOUTME: e2e tests for every MCP tool against a live Cyoda backend
# ABOUTME: detects Cyoda HTTP API regressions by calling tool functions directly

from typing import Optional

import pytest

# Run all tests in this module within a single session-scoped event loop.
# This prevents cross-loop errors from httpx connection pools held by the
# singleton AsyncTokenFetcher service across test function boundaries.
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio(loop_scope="session")]

from cyoda_mcp.tools.edge_message import (
    get_edge_message_tool,
    send_edge_message_tool,
)
from cyoda_mcp.tools.entity_management import (
    create_entity_tool,
    delete_entity_tool,
    get_entity_tool,
    list_entities_tool,
    update_entity_tool,
)
from cyoda_mcp.tools.search import find_all, search
from cyoda_mcp.tools.workflow_management import (
    export_workflows_to_file_tool,
    import_workflows_from_file_tool,
    list_workflow_files_tool,
    validate_workflow_file_tool,
)

# FastMCP wraps each tool function in a FunctionTool descriptor.
# Access .fn to get the original async Python function for direct invocation.
_create_entity = create_entity_tool.fn
_get_entity = get_entity_tool.fn
_list_entities = list_entities_tool.fn
_update_entity = update_entity_tool.fn
_delete_entity = delete_entity_tool.fn
_find_all = find_all.fn
_search = search.fn
_import_workflows = import_workflows_from_file_tool.fn
_export_workflows = export_workflows_to_file_tool.fn
_list_workflow_files = list_workflow_files_tool.fn
_validate_workflow_file = validate_workflow_file_tool.fn
_send_edge_message = send_edge_message_tool.fn
_get_edge_message = get_edge_message_tool.fn

ENTITY_MODEL = "exampleentity"
ENTITY_VERSION = "1"
WORKFLOW_FILE = "example_application/resources/workflow/example_entity/version_1/ExampleEntity.json"
WORKFLOW_BASE_DIR = "example_application/resources/workflow"

TEST_ENTITY_DATA = {
    "name": "MCP E2E Test Entity",
    "description": "Created by automated e2e tests to verify MCP tool functionality",
    "category": "ELECTRONICS",
    "isActive": True,
}


class TestWorkflowTools:
    """Tests for workflow management MCP tools."""

    async def test_import_workflows_from_file_tool(self):
        result = await _import_workflows(
            entity_name=ENTITY_MODEL,
            model_version=ENTITY_VERSION,
            file_path=WORKFLOW_FILE,
            import_mode="REPLACE",
        )
        assert result.get("success") is True, f"Workflow import failed: {result.get('error')}"

    async def test_export_workflows_to_file_tool(self, tmp_path):
        export_path = str(tmp_path / "exported_workflow.json")
        result = await _export_workflows(
            entity_name=ENTITY_MODEL,
            model_version=ENTITY_VERSION,
            file_path=export_path,
        )
        assert result.get("success") is True, f"Workflow export failed: {result.get('error')}"
        assert result.get("workflows_count", 0) > 0, "Expected at least one exported workflow"

    async def test_list_workflow_files_tool(self):
        result = await _list_workflow_files(base_path=WORKFLOW_BASE_DIR)
        assert result.get("success") is True, f"List workflow files failed: {result.get('error')}"
        assert result.get("files_count", 0) > 0, "Expected workflow files to exist on disk"

    async def test_validate_workflow_file_tool(self):
        result = await _validate_workflow_file(file_path=WORKFLOW_FILE)
        assert result.get("success") is True, f"Workflow validation failed: {result.get('error')}"
        assert result.get("is_valid") is True, f"Workflow file is not valid: {result.get('errors')}"


class TestEntityManagementTools:
    """Tests for entity CRUD MCP tools.

    Tests are declared in lifecycle order: create → list → get → update → delete.
    The entity_id is shared via a class attribute between tests in this sequence.
    If create fails, subsequent tests that depend on entity_id will be skipped.
    """

    entity_id: Optional[str] = None

    async def test_create_entity_tool(self):
        result = await _create_entity(
            entity_model=ENTITY_MODEL,
            entity_data=TEST_ENTITY_DATA,
            entity_version=ENTITY_VERSION,
        )
        assert result.get("success") is True, f"Entity creation failed: {result.get('error')}"
        assert result.get("entity_id"), "Expected a non-empty entity_id in create response"
        TestEntityManagementTools.entity_id = result["entity_id"]

    async def test_list_entities_tool(self):
        result = await _list_entities(
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
        )
        assert result.get("success") is True, f"List entities failed: {result.get('error')}"
        assert isinstance(result.get("entities"), list), "Expected 'entities' to be a list"
        assert "count" in result, "Expected 'count' in list response"

    async def test_get_entity_tool(self):
        if not TestEntityManagementTools.entity_id:
            pytest.skip("Skipped: test_create_entity_tool did not produce an entity_id")
        result = await _get_entity(
            entity_model=ENTITY_MODEL,
            entity_id=TestEntityManagementTools.entity_id,
            entity_version=ENTITY_VERSION,
        )
        assert result.get("success") is True, f"Get entity failed: {result.get('error')}"
        assert result.get("data") is not None, "Expected 'data' in get response"
        assert result.get("metadata", {}).get("id") == TestEntityManagementTools.entity_id

    async def test_update_entity_tool(self):
        if not TestEntityManagementTools.entity_id:
            pytest.skip("Skipped: test_create_entity_tool did not produce an entity_id")
        updated_data = {**TEST_ENTITY_DATA, "description": "Updated by MCP e2e test"}
        result = await _update_entity(
            entity_model=ENTITY_MODEL,
            entity_id=TestEntityManagementTools.entity_id,
            entity_data=updated_data,
            entity_version=ENTITY_VERSION,
        )
        assert result.get("success") is True, f"Update entity failed: {result.get('error')}"
        assert result.get("entity_id"), "Expected entity_id in update response"

    async def test_delete_entity_tool(self):
        if not TestEntityManagementTools.entity_id:
            pytest.skip("Skipped: test_create_entity_tool did not produce an entity_id")
        result = await _delete_entity(
            entity_model=ENTITY_MODEL,
            entity_id=TestEntityManagementTools.entity_id,
            entity_version=ENTITY_VERSION,
        )
        assert result.get("success") is True, f"Delete entity failed: {result.get('error')}"
        TestEntityManagementTools.entity_id = None


class TestSearchTools:
    """Tests for search MCP tools against the live Cyoda backend."""

    async def test_find_all(self):
        result = await _find_all(entity_model=ENTITY_MODEL, entity_version=ENTITY_VERSION)
        assert result.get("success") is True, f"find_all failed: {result.get('error')}"
        assert isinstance(result.get("entities"), list), "Expected 'entities' to be a list"
        assert "count" in result, "Expected 'count' in find_all response"

    async def test_search_with_simple_field_conditions(self):
        # Backward-compatible simple field=value pair syntax
        result = await _search(
            entity_model=ENTITY_MODEL,
            search_conditions={"category": "ELECTRONICS"},
            entity_version=ENTITY_VERSION,
        )
        assert result.get("success") is True, f"search (simple) failed: {result.get('error')}"
        assert isinstance(result.get("entities"), list), "Expected 'entities' to be a list"

    async def test_search_with_cyoda_group_conditions(self):
        # Cyoda-native group condition syntax
        result = await _search(
            entity_model=ENTITY_MODEL,
            search_conditions={
                "type": "group",
                "operator": "AND",
                "conditions": [
                    {
                        "type": "simple",
                        "jsonPath": "$.category",
                        "operatorType": "EQUALS",
                        "value": "ELECTRONICS",
                    }
                ],
            },
            entity_version=ENTITY_VERSION,
        )
        assert result.get("success") is True, f"search (group) failed: {result.get('error')}"
        assert isinstance(result.get("entities"), list), "Expected 'entities' to be a list"

    async def test_search_with_lifecycle_condition(self):
        # Lifecycle (state-based) condition syntax
        result = await _search(
            entity_model=ENTITY_MODEL,
            search_conditions={
                "type": "lifecycle",
                "field": "state",
                "operatorType": "EQUALS",
                "value": "created",
            },
            entity_version=ENTITY_VERSION,
        )
        assert result.get("success") is True, f"search (lifecycle) failed: {result.get('error')}"
        assert isinstance(result.get("entities"), list), "Expected 'entities' to be a list"


class TestEdgeMessageTools:
    """Tests for edge message MCP tools against the live Cyoda backend."""

    async def test_send_edge_message_tool(self):
        result = await _send_edge_message(
            subject="mcp.e2e.test",
            content={"source": "mcp-e2e-tests", "purpose": "regression detection"},
            correlation_id="mcp-e2e-test-send",
        )
        assert result.get("success") is True, f"send_edge_message failed: {result.get('error')}"
        assert "entity_ids" in result, "Expected 'entity_ids' in send response"

    async def test_get_edge_message_tool(self):
        # Send a message without specifying message_id; Cyoda assigns a UUID v1
        send_result = await _send_edge_message(
            subject="mcp.e2e.test",
            content={"source": "mcp-e2e-tests", "purpose": "get-message-test"},
        )
        assert send_result.get("success") is True, (
            f"Prerequisite send failed before get test: {send_result.get('error')}"
        )

        # The returned entity_ids contain the UUID v1 assigned by Cyoda
        entity_ids = send_result.get("entity_ids", [])
        assert entity_ids, "Expected at least one entity_id in send response"
        message_uuid = entity_ids[0]

        result = await _get_edge_message(message_id=message_uuid)
        assert result.get("success") is True, f"get_edge_message failed: {result.get('error')}"
        assert result.get("message_id") is not None

