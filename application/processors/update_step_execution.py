"""
Processor: update_step_execution
Purpose: Update the StepExecution entity's status/evidence. Implements Atomic Failure logic: on a 'Failed' step, mark parent TestRunExecution as 'Failed'.

Implementation notes:
- Uses data_client to update step execution and, if failure, update parent run execution and optionally trigger cancellation.
"""

from typing import Dict, Any

try:
    from application.clients.data_client import data_client
except Exception:
    data_client = None


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    context = context or {}

    step_execution_id = event.get("step_execution_id")
    new_status = event.get("new_status")
    evidence = event.get("evidence", [])

    if not step_execution_id or not new_status:
        return {"status": "error", "errors": ["step_execution_id and new_status are required"]}

    if data_client is None:
        return {"status": "error", "errors": ["data_client not available. Implement application.clients.data_client.data_client"]}

    # Load step execution
    step_exec = data_client.get_step_execution(step_execution_id)
    if not step_exec:
        return {"status": "error", "errors": [f"StepExecution not found: {step_execution_id}"]}

    # Update step execution
    update_payload = {"status": new_status, "evidence": evidence}
    data_client.update_step_execution(step_execution_id, update_payload)

    result = {"status": "ok", "updated_step_execution": step_execution_id, "new_status": new_status}

    # Atomic Failure logic
    if new_status.lower() == "failed":
        parent_run_exec_id = step_exec.get("run_execution_id") or step_exec.get("runexec_id")
        if parent_run_exec_id:
            # Update parent TestRunExecution overall_status to 'Failed'
            data_client.update_test_run_execution(parent_run_exec_id, {"overall_status": "Failed"})
            result["atomic_failure_applied"] = True
            result["updated_parent_run_execution"] = parent_run_exec_id

            # Optionally cancel/short-circuit remaining TestRunExecution items
            # data_client.cancel_remaining_run_executions(parent_run_exec_id)

    return result
