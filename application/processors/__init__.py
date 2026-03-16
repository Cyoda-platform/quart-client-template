"""Processor registry module
Generated registry for processors used by workflows.
"""

from .allocate_test_run_executions import handle as allocate_test_run_executions
from .create_step_executions import handle as create_step_executions
from .update_step_execution import handle as update_step_execution
from .aggregate_run_metrics import handle as aggregate_run_metrics
from .lock_run import handle as lock_run

processors_manifest = [
    {
        "name": "allocate_test_run_executions",
        "workflow": "TestRunExecutionWorkflow",
        "state": "initialized",
        "executionMode": "SYNC",
        "attachEntity": True
n    },
    {
        "name": "create_step_executions",
        "workflow": "TestRunExecutionWorkflow",
        "state": "initialized",
        "executionMode": "SYNC",
        "attachEntity": True
    },
    {
        "name": "update_step_execution",
        "workflow": "TestRunExecutionWorkflow",
        "event": "UPDATE_STEP_STATUS",
        "executionMode": "SYNC",
        "attachEntity": True
    },
    {
        "name": "aggregate_run_metrics",
        "workflow": "TestRunExecutionWorkflow",
        "state": "in_progress",
        "executionMode": "ASYNC_NEW_TX",
        "attachEntity": False
    },
    {
        "name": "lock_run",
        "workflow": "TestRunExecutionWorkflow",
        "state": "completed_locked",
        "executionMode": "SYNC",
        "attachEntity": True
    }
]
