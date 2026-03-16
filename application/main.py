from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import datetime

from application.clients.data_client import data_client
from application.processors import (
    allocate_test_run_executions,
    create_step_executions,
    update_step_execution,
    aggregate_run_metrics,
    lock_run,
)

app = FastAPI(title="Test Management System - API", version="0.1.0")


class TestRunCreateRequest(BaseModel):
    id: Optional[str]
    project_id: str
    title: Optional[str]
    suite_id: Optional[str]
    test_case_refs: Optional[List[str]] = None
    environment: Optional[str] = None
    created_by: Optional[str] = None


class UpdateStepStatusRequest(BaseModel):
    step_execution_id: str
    new_status: str
    evidence: Optional[List[str]] = None


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat() + "Z"}


@app.post("/test-runs", status_code=201)
def create_test_run(req: TestRunCreateRequest):
    run_id = req.id or f"run-{uuid.uuid4().hex[:8]}"
    payload = {
        "id": run_id,
        "title": req.title or "",
        "project_id": req.project_id,
        "suite_id": req.suite_id,
        "test_case_refs": req.test_case_refs or [],
        "environment": req.environment,
        "created_by": req.created_by,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    data_client.create_test_run(run_id, payload)
    return {"status": "created", "run_id": run_id}


@app.post("/test-runs/{run_id}/start")
def start_execution(run_id: str, created_by: Optional[str] = None):
    # Ensure run exists
    tr = data_client.get_test_run(run_id)
    if not tr:
        raise HTTPException(status_code=404, detail=f"TestRun {run_id} not found")

    # Trigger allocate_test_run_executions
    alloc_event = {"run_id": run_id, "project_id": tr.get("project_id"), "created_by": created_by or tr.get("created_by"), "test_case_refs": tr.get("test_case_refs")}    
    alloc_res = allocate_test_run_executions(alloc_event)
    if alloc_res.get("status") != "ok":
        raise HTTPException(status_code=500, detail={"error": "allocation_failed", "details": alloc_res})

    created_run_executions = alloc_res.get("created_run_executions", [])

    # Create step executions
    create_event = {"run_execution_ids": created_run_executions, "run_id": run_id}
    create_res = create_step_executions(create_event)
    if create_res.get("status") != "ok":
        raise HTTPException(status_code=500, detail={"error": "create_steps_failed", "details": create_res})

    # Update run status
    data_client.update_test_run(run_id, {"status": "in_progress", "started_at": datetime.datetime.utcnow().isoformat() + "Z"})

    # Kick off initial metrics aggregation (async style in prod)
    try:
        aggregate_run_metrics({"run_id": run_id})
    except Exception:
        pass

    return {"status": "started", "run_id": run_id, "created_run_executions": created_run_executions}


@app.post("/events/update-step-status")
def post_update_step_status(req: UpdateStepStatusRequest):
    # Update step execution and apply Atomic Failure logic
    ev = {"step_execution_id": req.step_execution_id, "new_status": req.new_status, "evidence": req.evidence or []}
    res = update_step_execution(ev)
    if res.get("status") != "ok":
        raise HTTPException(status_code=500, detail=res)

    # Recompute metrics for the run (if possible)
    # Attempt to determine run_id from step execution
    step = data_client.get_step_execution(req.step_execution_id)
    run_id = None
    if step:
        run_exec_id = step.get("run_execution_id")
        re = data_client.get_test_run_execution(run_exec_id) if run_exec_id else None
        if re:
            run_id = re.get("run_id")

    if run_id:
        aggregate_run_metrics({"run_id": run_id})

    return {"status": "ok", "update": res}


@app.get("/reports/{run_id}")
def get_report(run_id: str):
    report = data_client.execution_reports.get(run_id)
    if not report:
        # Try to compute minimal report
        step_execs = data_client.list_step_executions_for_run(run_id)
        report = {
            "passed_count": sum(1 for s in step_execs if s.get("status") == "Passed"),
            "failed_count": sum(1 for s in step_execs if s.get("status") == "Failed"),
            "untested_count": sum(1 for s in step_execs if s.get("status") in ("Untested", None)),
            "duration_ms": 0,
        }
    return {"run_id": run_id, "report": report}


@app.post("/test-runs/{run_id}/complete")
def complete_run(run_id: str):
    tr = data_client.get_test_run(run_id)
    if not tr:
        raise HTTPException(status_code=404, detail=f"TestRun {run_id} not found")

    # Mark run as completed and lock
    data_client.update_test_run(run_id, {"status": "completed", "finished_at": datetime.datetime.utcnow().isoformat() + "Z"})
    lock_run({"run_id": run_id})

    return {"status": "locked", "run_id": run_id}
