"""
Processor: lock_run
Purpose: Mark a TestRun and its child TestRunExecution and StepExecution entities as locked/read-only.
Location: application/processors/lock_run.py

Interface: handle(event, context)
- event: {"run_id": "..."}

Behavior (stub):
- Validate input
- Mark records as locked (TODO: data layer ops)
- Return success
"""

from typing import Dict, Any


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    context = context or {}

    run_id = event.get("run_id")
    if not run_id:
        return {"status": "error", "errors": ["run_id is required"]}

    # TODO: Perform data layer operations to set locked=True on TestRun, TestRunExecution, StepExecution
    # data_client.lock_test_run(run_id)

    return {"status": "ok", "run_id": run_id, "locked": True}
