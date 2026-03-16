"""
Processor: aggregate_run_metrics
Purpose: Recalculate Passed/Failed/Untested counts and duration for a TestRun in real-time and update ExecutionReport or run summary.

Implementation notes:
- Uses data_client to query step executions for the run and compute metrics.
- Persists an ExecutionReport entity or updates TestRun summary fields.
"""

from typing import Dict, Any
from datetime import datetime

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

    # Query all step executions for the run via data client
    step_execs = data_client.list_step_executions_for_run(run_id)

    passed = sum(1 for s in step_execs if s.get("status") == "Passed")
    failed = sum(1 for s in step_execs if s.get("status") == "Failed")
    untested = sum(1 for s in step_execs if s.get("status") in ("Untested", None))

    # Compute duration as difference between earliest started_at and latest finished_at
    started_times = [s.get("started_at") for s in step_execs if s.get("started_at")]
    finished_times = [s.get("finished_at") for s in step_execs if s.get("finished_at")]

    duration_ms = 0
    if started_times and finished_times:
        # Parse ISO timestamps if necessary
        try:
            start = min(datetime.fromisoformat(t) for t in started_times)
            finish = max(datetime.fromisoformat(t) for t in finished_times)
            duration_ms = int((finish - start).total_seconds() * 1000)
        except Exception:
            duration_ms = 0

    metrics = {
        "passed_count": passed,
        "failed_count": failed,
        "untested_count": untested,
        "duration_ms": duration_ms,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }

    # Persist ExecutionReport or update TestRun summary
    data_client.upsert_execution_report(run_id, metrics)

    return {"status": "ok", "run_id": run_id, "metrics": metrics}
