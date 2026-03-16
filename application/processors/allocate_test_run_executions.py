"""
Processor: allocate_test_run_executions
Purpose: Given a TestRun entity, create immutable TestRunExecution snapshots for each referenced TestCase.
Location: application/processors/allocate_test_run_executions.py

Interface: handle(event, context)
- event: dict containing at minimum {"run_id": "...", "project_id": "..."}
- context: dict (optional runtime context)

Behavior (implemented):
- Validate input
- Load TestRun entity via data_client.get_test_run(run_id)
- For each test_case_ref, load TestCase and create TestRunExecution snapshot via data_client.create_test_run_execution
- Attach automation metadata from TestCase if present
- Return list of created run execution ids

Notes:
- This implementation expects a data client available at application.clients.data_client.data_client
- Replace / extend the data_client methods used below to match your environment.
"""

from typing import Dict, Any, List

try:
    from application.clients.data_client import data_client
except Exception:
    data_client = None


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Allocate TestRunExecution snapshots for a TestRun using the platform data client.

    Expected event payload example:
    {
        "run_id": "run-0001",
        "project_id": "project-0001",
        "created_by": "user-0001"
    }
    """
    context = context or {}

    run_id = event.get("run_id")
    if not run_id:
        return {"status": "error", "errors": ["run_id is required"]}

    if data_client is None:
        return {"status": "error", "errors": ["data_client not available. Implement application.clients.data_client.data_client"]}

    # Load TestRun
    test_run = data_client.get_test_run(run_id)
    if not test_run:
        return {"status": "error", "errors": [f"TestRun not found: {run_id}"]}

    test_case_ids = test_run.get("test_case_refs") or []

    created: List[str] = []
    for tc_id in test_case_ids:
        # Load TestCase to copy snapshot
        tc = data_client.get_test_case(tc_id)
        if not tc:
            # skip or record error per policy
            continue

        snapshot = {
            "test_case_id": tc_id,
            "title": tc.get("title"),
            "description": tc.get("description"),
            "steps": tc.get("steps", []),
            "automation_metadata": tc.get("automation_metadata"),
            "copied_from": tc_id,
            "status": "Queued",
        }

        # Persist TestRunExecution (immutable snapshot)
        created_id = data_client.create_test_run_execution(run_id=run_id, snapshot=snapshot, created_by=event.get("created_by"))
        created.append(created_id)

    return {"status": "ok", "created_run_executions": created}
