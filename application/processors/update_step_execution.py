"""
Processor: update_step_execution
Purpose: Update the StepExecution entity's status/evidence. Implements Atomic Failure logic: on a 'Failed' step, mark parent TestRunExecution as 'Failed'.
Location: application/processors/update_step_execution.py

Interface: handle(event, context)
- event: {"step_execution_id": "...", "new_status": "Passed|Failed|Error|Skipped", "evidence": [...]} 

Behavior (stub):
- Basic validation
- Update StepExecution record
- If new_status == 'Failed', set parent TestRunExecution overall_status to 'Failed' (Atomic Failure)
- Return updated entities
"""

from typing import Dict, Any


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    context = context or {}

    step_execution_id = event.get("step_execution_id")
    new_status = event.get("new_status")
    if not step_execution_id or not new_status:
        return {"status": "error", "errors": ["step_execution_id and new_status are required"]}

    # TODO: Load step execution from data client
    # step_exec = data_client.get_step_execution(step_execution_id)
    # Simulate parent mapping
    parent_run_exec_id = "runexec-testcase-0001"

    # TODO: persists status update
    # data_client.update_step_execution(step_execution_id, {"status": new_status, "evidence": event.get('evidence',[])})

    result = {"status": "ok", "updated_step_execution": step_execution_id, "new_status": new_status}

    # Atomic Failure logic
    if new_status.lower() == "failed":
        # TODO: update parent TestRunExecution overall_status to 'Failed'
        # data_client.update_test_run_execution(parent_run_exec_id, {"overall_status": "Failed"})
        result["atomic_failure_applied"] = True
        result["updated_parent_run_execution"] = parent_run_exec_id

        # TODO: Optionally trigger cancellation of remaining executions

    return result
