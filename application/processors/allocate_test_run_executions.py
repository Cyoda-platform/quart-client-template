"""
Processor: allocate_test_run_executions
Purpose: Given a TestRun entity, create immutable TestRunExecution snapshots for each referenced TestCase.
Location: application/processors/allocate_test_run_executions.py

Interface: handle(event, context)
- event: dict containing at minimum {"run_id": "...", "project_id": "..."}
- context: dict (optional runtime context)

Behavior (stub):
- Validate input
- Load TestRun entity (TODO: integrate with data client)
- For each test_case_ref, create TestRunExecution entity with a snapshot of the TestCase
- Attach automation metadata from TestCase if present
- Return list of created run execution ids

Note: This is a stub intended to be extended with Cyoda data client calls.
"""

from typing import Dict, Any, List


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Allocate TestRunExecution snapshots for a TestRun.

    Expected event payload example:
    {
        "run_id": "run-0001",
        "project_id": "project-0001",
        "created_by": "user-0001"
    }
    """
    context = context or {}

    # Basic validation
    run_id = event.get("run_id")
    if not run_id:
        return {"status": "error", "errors": ["run_id is required"]}

    # TODO: Replace with actual data access layer calls to fetch TestRun and TestCases
    # Example pseudo-code:
    # test_run = data_client.get_test_run(run_id)
    # test_case_ids = test_run.get("test_case_refs") or []

    # For now, simulate behavior with placeholders
    test_case_ids = event.get("test_case_refs", ["testcase-0001"])  # TODO

    created = []
    for tc_id in test_case_ids:
        # Build immutable snapshot (in real impl, copy the TestCase data)
        snapshot = {
            "test_case_id": tc_id,
            "snapshot_meta": {
                "copied_from": tc_id,
            },
            "status": "Queued",
        }
        # TODO: persist TestRunExecution entity via data_client
        # created_id = data_client.create_test_run_execution(run_id, snapshot)
        created_id = f"runexec-{tc_id}"
        created.append(created_id)

    return {"status": "ok", "created_run_executions": created}
