"""
Processor: create_step_executions
Purpose: For each TestRunExecution snapshot, create StepExecution entries for every step in the snapshot.
Location: application/processors/create_step_executions.py

Interface: handle(event, context)
- event: { "run_execution_ids": [...], "run_id": "..." }

Behavior (stub):
- Validate input
- For each run execution id, load its snapshot and create StepExecution entities with status 'Untested'
- Return created step execution ids
"""

from typing import Dict, Any, List


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    context = context or {}

    run_execution_ids = event.get("run_execution_ids")
    if not run_execution_ids:
        return {"status": "error", "errors": ["run_execution_ids is required"]}

    created = {}
    for re_id in run_execution_ids:
        # TODO: load TestRunExecution snapshot using data client
        # snapshot = data_client.get_test_run_execution(re_id)
        # For stub, assume snapshot contains 3 steps
        steps = [
            {"step_number": 1, "action": "Navigate to login page", "expected": "Login page is displayed"},
            {"step_number": 2, "action": "Enter credentials", "expected": "Credentials are entered"},
            {"step_number": 3, "action": "Click login", "expected": "User lands on dashboard"}
        ]

        step_ids = []
        for s in steps:
            # Create StepExecution entity with status 'Untested'
            # TODO: persist via data client
            step_id = f"stepexec-{re_id}-{s['step_number']}"
            step_ids.append(step_id)
        created[re_id] = step_ids

    return {"status": "ok", "created_step_executions": created}
