"""
Processor: create_step_executions
Purpose: For each TestRunExecution snapshot, create StepExecution entries for every step in the snapshot.

Implementation notes:
- Uses data_client to read TestRunExecution snapshot and create StepExecution entities.
- Creates StepExecution with status 'Untested' and attaches them to the parent TestRunExecution.
"""

from typing import Dict, Any, List

try:
    from application.clients.data_client import data_client
except Exception:
    data_client = None


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    context = context or {}

    run_execution_ids = event.get("run_execution_ids") or event.get("created_run_executions")
    if not run_execution_ids:
        return {"status": "error", "errors": ["run_execution_ids is required"]}

    if data_client is None:
        return {"status": "error", "errors": ["data_client not available. Implement application.clients.data_client.data_client"]}

    created = {}
    for re_id in run_execution_ids:
        snapshot = data_client.get_test_run_execution(re_id)
        if not snapshot:
            continue

        steps = snapshot.get("steps", [])
        step_ids = []
        for s in steps:
            payload = {
                "run_execution_id": re_id,
                "test_step_number": s.get("step_number"),
                "action": s.get("action"),
                "expected": s.get("expected"),
                "status": "Untested",
                "evidence": [],
            }
            step_id = data_client.create_step_execution(run_execution_id=re_id, payload=payload)
            step_ids.append(step_id)

        # Optionally update the TestRunExecution with list of step ids
        data_client.update_test_run_execution(re_id, {"step_execution_ids": step_ids})
        created[re_id] = step_ids

    return {"status": "ok", "created_step_executions": created}
