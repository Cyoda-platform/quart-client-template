"""
Processor: lock_run
Purpose: Mark a TestRun and its child TestRunExecution and StepExecution entities as locked/read-only.

Implementation notes:
- Uses data_client to set locked=True on TestRun, TestRunExecution and StepExecution entities.
- Enforcing rejection of inbound updates should be handled by data layer checks.
"""

from typing import Dict, Any

try:
    from application.clients.data_client import data_client
except Exception:
    data_client = None


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    context = context or {}

    run_id = event.get("run_id")
    if not run_id:
        return {"status": "error", "errors": ["run_id is required"]}

    if data_client is None:
        return {"status": "error", "errors": ["data_client not available. Implement application.clients.data_client.data_client"]}

    # Lock TestRun
    data_client.update_test_run(run_id, {"locked": True})

    # Lock child TestRunExecutions
    run_execs = data_client.list_test_run_executions_for_run(run_id)
    for re in run_execs:
        data_client.update_test_run_execution(re.get("id"), {"locked": True})
        # Lock their step executions
        steps = data_client.list_step_executions_for_run_execution(re.get("id"))
        for s in steps:
            data_client.update_step_execution(s.get("id"), {"locked": True})

    return {"status": "ok", "run_id": run_id, "locked": True}
