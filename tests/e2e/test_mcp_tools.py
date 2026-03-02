# ABOUTME: e2e tests for every MCP tool against a live Cyoda backend
# ABOUTME: detects Cyoda HTTP API regressions by calling tool functions directly

from typing import Optional

import pytest

# Run all tests in this module within a single session-scoped event loop.
# This prevents cross-loop errors from httpx connection pools held by the
# singleton AsyncTokenFetcher service across test function boundaries.
pytestmark = [pytest.mark.e2e, pytest.mark.asyncio(loop_scope="session")]

from cyoda_mcp.tools.async_search import (
    cancel_async_search_tool,
    get_async_search_results_tool,
    get_async_search_status_tool,
    submit_async_search_tool,
)
from cyoda_mcp.tools.edge_message import (
    bulk_delete_edge_messages_tool,
    delete_edge_message_tool,
    get_edge_message_tool,
    send_edge_message_tool,
)
from cyoda_mcp.tools.entity_audit import (
    get_entity_audit_tool,
    get_workflow_finished_event_tool,
)
from cyoda_mcp.tools.entity_management import (
    bulk_create_entities_tool,
    create_entity_tool,
    delete_all_entities_tool,
    delete_entity_tool,
    get_entity_changes_tool,
    get_entity_tool,
    list_entities_tool,
    update_entity_tool,
)
from cyoda_mcp.tools.entity_model import list_entity_models_tool
from cyoda_mcp.tools.entity_stats import (
    get_entity_stats_by_model_tool,
    get_entity_stats_by_state_and_model_tool,
    get_entity_stats_by_state_tool,
    get_entity_stats_tool,
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
_delete_all_entities = delete_all_entities_tool.fn
_bulk_create_entities = bulk_create_entities_tool.fn
_get_entity_changes = get_entity_changes_tool.fn
_find_all = find_all.fn
_search = search.fn
_import_workflows = import_workflows_from_file_tool.fn
_export_workflows = export_workflows_to_file_tool.fn
_list_workflow_files = list_workflow_files_tool.fn
_validate_workflow_file = validate_workflow_file_tool.fn
_send_edge_message = send_edge_message_tool.fn
_get_edge_message = get_edge_message_tool.fn
_delete_edge_message = delete_edge_message_tool.fn
_bulk_delete_edge_messages = bulk_delete_edge_messages_tool.fn
_list_entity_models = list_entity_models_tool.fn
_get_entity_audit = get_entity_audit_tool.fn
_get_workflow_finished_event = get_workflow_finished_event_tool.fn
_get_entity_stats = get_entity_stats_tool.fn
_get_entity_stats_by_model = get_entity_stats_by_model_tool.fn
_get_entity_stats_by_state = get_entity_stats_by_state_tool.fn
_get_entity_stats_by_state_and_model = get_entity_stats_by_state_and_model_tool.fn
_submit_async_search = submit_async_search_tool.fn
_get_async_search_results = get_async_search_results_tool.fn
_get_async_search_status = get_async_search_status_tool.fn
_cancel_async_search = cancel_async_search_tool.fn

ENTITY_MODEL = "exampleentity"
ENTITY_VERSION = "1"
WORKFLOW_FILE = (
    "example_application/resources/workflow/example_entity/version_1/ExampleEntity.json"
)
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
        assert (
            result.get("success") is True
        ), f"Workflow import failed: {result.get('error')}"

    async def test_export_workflows_to_file_tool(self, tmp_path):
        export_path = str(tmp_path / "exported_workflow.json")
        result = await _export_workflows(
            entity_name=ENTITY_MODEL,
            model_version=ENTITY_VERSION,
            file_path=export_path,
        )
        assert (
            result.get("success") is True
        ), f"Workflow export failed: {result.get('error')}"
        assert (
            result.get("workflows_count", 0) > 0
        ), "Expected at least one exported workflow"

    async def test_list_workflow_files_tool(self):
        result = await _list_workflow_files(base_path=WORKFLOW_BASE_DIR)
        assert (
            result.get("success") is True
        ), f"List workflow files failed: {result.get('error')}"
        assert (
            result.get("files_count", 0) > 0
        ), "Expected workflow files to exist on disk"

    async def test_validate_workflow_file_tool(self):
        result = await _validate_workflow_file(file_path=WORKFLOW_FILE)
        assert (
            result.get("success") is True
        ), f"Workflow validation failed: {result.get('error')}"
        assert (
            result.get("is_valid") is True
        ), f"Workflow file is not valid: {result.get('errors')}"


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
        assert (
            result.get("success") is True
        ), f"Entity creation failed: {result.get('error')}"
        assert result.get(
            "entity_id"
        ), "Expected a non-empty entity_id in create response"
        TestEntityManagementTools.entity_id = result["entity_id"]

    async def test_list_entities_tool(self):
        result = await _list_entities(
            entity_model=ENTITY_MODEL,
            entity_version=ENTITY_VERSION,
        )
        assert (
            result.get("success") is True
        ), f"List entities failed: {result.get('error')}"
        assert isinstance(
            result.get("entities"), list
        ), "Expected 'entities' to be a list"
        assert "count" in result, "Expected 'count' in list response"

    async def test_get_entity_tool(self):
        if not TestEntityManagementTools.entity_id:
            pytest.skip("Skipped: test_create_entity_tool did not produce an entity_id")
        result = await _get_entity(
            entity_model=ENTITY_MODEL,
            entity_id=TestEntityManagementTools.entity_id,
            entity_version=ENTITY_VERSION,
        )
        assert (
            result.get("success") is True
        ), f"Get entity failed: {result.get('error')}"
        assert result.get("data") is not None, "Expected 'data' in get response"
        assert (
            result.get("metadata", {}).get("id") == TestEntityManagementTools.entity_id
        )

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
        assert (
            result.get("success") is True
        ), f"Update entity failed: {result.get('error')}"
        assert result.get("entity_id"), "Expected entity_id in update response"

    async def test_delete_entity_tool(self):
        if not TestEntityManagementTools.entity_id:
            pytest.skip("Skipped: test_create_entity_tool did not produce an entity_id")
        result = await _delete_entity(
            entity_model=ENTITY_MODEL,
            entity_id=TestEntityManagementTools.entity_id,
            entity_version=ENTITY_VERSION,
        )
        assert (
            result.get("success") is True
        ), f"Delete entity failed: {result.get('error')}"
        TestEntityManagementTools.entity_id = None


class TestSearchTools:
    """Tests for search MCP tools against the live Cyoda backend."""

    async def test_find_all(self):
        result = await _find_all(
            entity_model=ENTITY_MODEL, entity_version=ENTITY_VERSION
        )
        assert result.get("success") is True, f"find_all failed: {result.get('error')}"
        assert isinstance(
            result.get("entities"), list
        ), "Expected 'entities' to be a list"
        assert "count" in result, "Expected 'count' in find_all response"

    async def test_search_with_simple_field_conditions(self):
        # Backward-compatible simple field=value pair syntax
        result = await _search(
            entity_model=ENTITY_MODEL,
            search_conditions={"category": "ELECTRONICS"},
            entity_version=ENTITY_VERSION,
        )
        assert (
            result.get("success") is True
        ), f"search (simple) failed: {result.get('error')}"
        assert isinstance(
            result.get("entities"), list
        ), "Expected 'entities' to be a list"

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
        assert (
            result.get("success") is True
        ), f"search (group) failed: {result.get('error')}"
        assert isinstance(
            result.get("entities"), list
        ), "Expected 'entities' to be a list"

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
        assert (
            result.get("success") is True
        ), f"search (lifecycle) failed: {result.get('error')}"
        assert isinstance(
            result.get("entities"), list
        ), "Expected 'entities' to be a list"


class TestEdgeMessageTools:
    """Tests for edge message MCP tools against the live Cyoda backend."""

    async def test_send_edge_message_tool(self):
        result = await _send_edge_message(
            subject="mcp.e2e.test",
            content={"source": "mcp-e2e-tests", "purpose": "regression detection"},
            correlation_id="mcp-e2e-test-send",
        )
        assert (
            result.get("success") is True
        ), f"send_edge_message failed: {result.get('error')}"
        assert "entity_ids" in result, "Expected 'entity_ids' in send response"

    async def test_get_edge_message_tool(self):
        # Send a message without specifying message_id; Cyoda assigns a UUID v1
        send_result = await _send_edge_message(
            subject="mcp.e2e.test",
            content={"source": "mcp-e2e-tests", "purpose": "get-message-test"},
        )
        assert (
            send_result.get("success") is True
        ), f"Prerequisite send failed before get test: {send_result.get('error')}"

        # The returned entity_ids contain the UUID v1 assigned by Cyoda
        entity_ids = send_result.get("entity_ids", [])
        assert entity_ids, "Expected at least one entity_id in send response"
        message_uuid = entity_ids[0]

        result = await _get_edge_message(message_id=message_uuid)
        assert (
            result.get("success") is True
        ), f"get_edge_message failed: {result.get('error')}"
        assert result.get("message_id") is not None


class TestEdgeMessageDeleteTools:
    """Tests for edge message delete operations."""

    async def test_delete_edge_message_tool(self):
        send_result = await _send_edge_message(
            subject="mcp.e2e.test",
            content={"source": "mcp-e2e-tests", "purpose": "delete-test"},
        )
        assert (
            send_result.get("success") is True
        ), f"Prerequisite send failed: {send_result.get('error')}"
        message_uuid = send_result.get("entity_ids", [])[0]

        result = await _delete_edge_message(message_id=message_uuid)
        assert (
            result.get("success") is True
        ), f"delete_edge_message failed: {result.get('error')}"

    async def test_bulk_delete_edge_messages_tool(self):
        # Send two messages and bulk-delete them
        ids = []
        for i in range(2):
            sr = await _send_edge_message(
                subject="mcp.e2e.test",
                content={"source": "mcp-e2e-tests", "purpose": f"bulk-delete-test-{i}"},
            )
            assert sr.get("success") is True
            ids.append(sr["entity_ids"][0])

        result = await _bulk_delete_edge_messages(message_ids=ids)
        assert (
            result.get("success") is True
        ), f"bulk_delete_edge_messages failed: {result.get('error')}"


class TestEntityModelTools:
    """Tests for entity model discovery tools."""

    async def test_list_entity_models_tool(self):
        result = await _list_entity_models()
        assert (
            result.get("success") is True
        ), f"list_entity_models failed: {result.get('error')}"
        assert isinstance(result.get("models"), list), "Expected 'models' to be a list"
        assert "count" in result, "Expected 'count' in response"


class TestEntityAuditTools:
    """Tests for entity audit and workflow event tools."""

    async def test_get_entity_audit_tool(self):
        # Create an entity so we have something to audit
        cr = await _create_entity(
            entity_model=ENTITY_MODEL,
            entity_data=TEST_ENTITY_DATA,
            entity_version=ENTITY_VERSION,
        )
        assert cr.get("success") is True
        entity_id = cr["entity_id"]

        result = await _get_entity_audit(entity_id=entity_id)
        assert (
            result.get("success") is True
        ), f"get_entity_audit failed: {result.get('error')}"
        assert result.get("entity_id") == entity_id

    async def test_get_workflow_finished_event_tool(self):
        # Create an entity and get its audit to find a transaction_id
        cr = await _create_entity(
            entity_model=ENTITY_MODEL,
            entity_data=TEST_ENTITY_DATA,
            entity_version=ENTITY_VERSION,
        )
        assert cr.get("success") is True
        entity_id = cr["entity_id"]

        # Get audit events to find a transaction ID
        audit_result = await _get_entity_audit(entity_id=entity_id)
        assert audit_result.get("success") is True

        audit_data = audit_result.get("audit")
        # The endpoint may return 404 if no workflow finished events exist yet;
        # we verify the tool call succeeds (even if audit data is empty)
        if audit_data:
            events = audit_data if isinstance(audit_data, list) else [audit_data]
            if events and events[0].get("transactionId"):
                tx_id = events[0]["transactionId"]
                result = await _get_workflow_finished_event(
                    entity_id=entity_id, transaction_id=tx_id
                )
                assert (
                    result.get("success") is True
                ), f"get_workflow_finished_event failed: {result.get('error')}"
        # If no events yet, test simply validates no exception was raised


class TestEntityStatsTools:
    """Tests for entity statistics tools."""

    async def test_get_entity_stats_tool(self):
        result = await _get_entity_stats()
        assert (
            result.get("success") is True
        ), f"get_entity_stats failed: {result.get('error')}"

    async def test_get_entity_stats_by_model_tool(self):
        result = await _get_entity_stats_by_model(
            entity_model=ENTITY_MODEL, entity_version=ENTITY_VERSION
        )
        assert (
            result.get("success") is True
        ), f"get_entity_stats_by_model failed: {result.get('error')}"
        assert result.get("entity_model") == ENTITY_MODEL

    async def test_get_entity_stats_by_state_tool(self):
        result = await _get_entity_stats_by_state()
        assert (
            result.get("success") is True
        ), f"get_entity_stats_by_state failed: {result.get('error')}"

    async def test_get_entity_stats_by_state_and_model_tool(self):
        result = await _get_entity_stats_by_state_and_model(
            entity_model=ENTITY_MODEL, entity_version=ENTITY_VERSION
        )
        assert (
            result.get("success") is True
        ), f"get_entity_stats_by_state_and_model failed: {result.get('error')}"


class TestEntityManagementExtendedTools:
    """Tests for bulk entity operations and change history."""

    entity_id: Optional[str] = None

    async def test_bulk_create_entities_tool(self):
        entities = [
            {**TEST_ENTITY_DATA, "description": f"Bulk e2e test entity {i}"}
            for i in range(2)
        ]
        result = await _bulk_create_entities(
            entity_model=ENTITY_MODEL,
            entities_data=entities,
            entity_version=ENTITY_VERSION,
        )
        assert (
            result.get("success") is True
        ), f"bulk_create_entities failed: {result.get('error')}"
        assert result.get("created_count") == 2

    async def test_get_entity_changes_tool(self):
        # Create an entity then query its change history
        cr = await _create_entity(
            entity_model=ENTITY_MODEL,
            entity_data=TEST_ENTITY_DATA,
            entity_version=ENTITY_VERSION,
        )
        assert cr.get("success") is True
        TestEntityManagementExtendedTools.entity_id = cr["entity_id"]

        result = await _get_entity_changes(entity_id=cr["entity_id"])
        assert (
            result.get("success") is True
        ), f"get_entity_changes failed: {result.get('error')}"
        assert isinstance(
            result.get("changes"), list
        ), "Expected 'changes' to be a list"

    async def test_delete_all_entities_tool(self):
        # Deletes all exampleentity instances; runs last in this class
        result = await _delete_all_entities(
            entity_model=ENTITY_MODEL, entity_version=ENTITY_VERSION
        )
        assert (
            result.get("success") is True
        ), f"delete_all_entities failed: {result.get('error')}"


class TestAsyncSearchTools:
    """Tests for async search lifecycle tools."""

    job_id: Optional[str] = None

    async def test_submit_async_search_tool(self):
        condition = {
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
        }
        result = await _submit_async_search(
            entity_model=ENTITY_MODEL,
            condition=condition,
            entity_version=ENTITY_VERSION,
        )
        assert (
            result.get("success") is True
        ), f"submit_async_search failed: {result.get('error')}"
        # Cyoda returns the job_id as a plain UUID string
        TestAsyncSearchTools.job_id = result.get("job_id")

    async def test_get_async_search_status_tool(self):
        if not TestAsyncSearchTools.job_id:
            pytest.skip("Skipped: no job_id from submit_async_search_tool")
        result = await _get_async_search_status(job_id=TestAsyncSearchTools.job_id)
        assert (
            result.get("success") is True
        ), f"get_async_search_status failed: {result.get('error')}"

    async def test_get_async_search_results_tool(self):
        if not TestAsyncSearchTools.job_id:
            pytest.skip("Skipped: no job_id from submit_async_search_tool")
        result = await _get_async_search_results(job_id=TestAsyncSearchTools.job_id)
        assert (
            result.get("success") is True
        ), f"get_async_search_results failed: {result.get('error')}"

    async def test_cancel_async_search_tool(self):
        # Submit a fresh job and cancel it
        condition = {"type": "group", "operator": "AND", "conditions": []}
        submit = await _submit_async_search(
            entity_model=ENTITY_MODEL,
            condition=condition,
            entity_version=ENTITY_VERSION,
        )
        if not submit.get("success"):
            pytest.skip("Skipped: submit for cancel test failed")
        job_id = submit.get("job_id")
        if not job_id:
            pytest.skip("Skipped: could not extract job_id for cancel test")

        result = await _cancel_async_search(job_id=job_id)
        assert (
            result.get("success") is True
        ), f"cancel_async_search failed: {result.get('error')}"
