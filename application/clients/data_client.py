"""
In-memory data client for tests and local development.

Provides a lightweight, mutable data store that implements the minimal
API expected by the TestRunExecutionWorkflow processors.

Note: This is a test helper and NOT intended for production.

Usage:
    from application.clients.data_client import data_client
    data_client.create_test_run({...})

Supported methods (used by processors):
- get_test_run(run_id)
- get_test_case(tc_id)
- create_test_run_execution(run_id, snapshot, created_by)
- get_test_run_execution(re_id)
- create_step_execution(run_execution_id, payload)
- update_test_run_execution(re_id, payload)
- update_step_execution(step_execution_id, payload)
- get_step_execution(step_execution_id)
- list_step_executions_for_run(run_id)
- upsert_execution_report(run_id, metrics)
- update_test_run(run_id, payload)
- list_test_run_executions_for_run(run_id)
- list_step_executions_for_run_execution(re_id)
- index_search_document(doc_id, doc)

"""
from typing import Dict, Any, List, Optional
from collections import defaultdict
import itertools
import datetime


class InMemoryDataClient:
    def __init__(self):
        # primary stores
        self.test_runs: Dict[str, Dict[str, Any]] = {}
        self.test_cases: Dict[str, Dict[str, Any]] = {}
        self.test_run_executions: Dict[str, Dict[str, Any]] = {}
        self.step_executions: Dict[str, Dict[str, Any]] = {}
        self.execution_reports: Dict[str, Dict[str, Any]] = {}

        # indices
        self.run_to_runexecs: Dict[str, List[str]] = defaultdict(list)
        self.runexec_to_steps: Dict[str, List[str]] = defaultdict(list)

        # simple in-memory search index
        self.search_index: Dict[str, Dict[str, Any]] = {}

        # id generators
        self._re_counter = itertools.count(1)
        self._se_counter = itertools.count(1)

    # --- TestRun operations ---
    def create_test_run(self, run_id: str, payload: Dict[str, Any]):
        payload.setdefault("id", run_id)
        self.test_runs[run_id] = payload
        return run_id

    def get_test_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self.test_runs.get(run_id)

    def update_test_run(self, run_id: str, payload: Dict[str, Any]) -> None:
        if run_id in self.test_runs:
            self.test_runs[run_id].update(payload)

    # --- TestCase operations ---
    def create_test_case(self, tc_id: str, payload: Dict[str, Any]):
        payload.setdefault("id", tc_id)
        self.test_cases[tc_id] = payload
        return tc_id

    def get_test_case(self, tc_id: str) -> Optional[Dict[str, Any]]:
        return self.test_cases.get(tc_id)

    def update_test_case(self, tc_id: str, payload: Dict[str, Any]) -> None:
        if tc_id in self.test_cases:
            self.test_cases[tc_id].update(payload)

    # --- TestRunExecution operations ---
    def create_test_run_execution(self, run_id: str, snapshot: Dict[str, Any], created_by: Optional[str] = None) -> str:
        idx = next(self._re_counter)
        re_id = f"runexec-{run_id}-{idx}"
        entity = {
            "id": re_id,
            "run_id": run_id,
            "snapshot": snapshot,
            "overall_status": snapshot.get("status", "Queued"),
            "created_by": created_by,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        self.test_run_executions[re_id] = entity
        self.run_to_runexecs[run_id].append(re_id)
        return re_id

    def get_test_run_execution(self, re_id: str) -> Optional[Dict[str, Any]]:
        return self.test_run_executions.get(re_id)

    def update_test_run_execution(self, re_id: str, payload: Dict[str, Any]) -> None:
        if re_id in self.test_run_executions:
            self.test_run_executions[re_id].update(payload)

    def list_test_run_executions_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        ids = self.run_to_runexecs.get(run_id, [])
        return [self.test_run_executions[rid] for rid in ids if rid in self.test_run_executions]

    # --- StepExecution operations ---
    def create_step_execution(self, run_execution_id: str, payload: Dict[str, Any]) -> str:
        idx = next(self._se_counter)
        se_id = f"stepexec-{idx}"
        entity = {
            "id": se_id,
            "run_execution_id": run_execution_id,
            "test_step_number": payload.get("test_step_number"),
            "action": payload.get("action"),
            "expected": payload.get("expected"),
            "status": payload.get("status", "Untested"),
            "evidence": payload.get("evidence", []),
            "started_at": payload.get("started_at"),
            "finished_at": payload.get("finished_at"),
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
        self.step_executions[se_id] = entity
        self.runexec_to_steps[run_execution_id].append(se_id)
        return se_id

    def get_step_execution(self, se_id: str) -> Optional[Dict[str, Any]]:
        return self.step_executions.get(se_id)

    def update_step_execution(self, se_id: str, payload: Dict[str, Any]) -> None:
        if se_id in self.step_executions:
            self.step_executions[se_id].update(payload)

    def list_step_executions_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        # gather all run exec ids and then their steps
        res = []
        for re in self.run_to_runexecs.get(run_id, []):
            for se_id in self.runexec_to_steps.get(re, []):
                if se_id in self.step_executions:
                    res.append(self.step_executions[se_id])
        return res

    def list_step_executions_for_run_execution(self, run_execution_id: str) -> List[Dict[str, Any]]:
        return [self.step_executions[sid] for sid in self.runexec_to_steps.get(run_execution_id, []) if sid in self.step_executions]

    # --- ExecutionReport operations ---
    def upsert_execution_report(self, run_id: str, metrics: Dict[str, Any]) -> None:
        self.execution_reports[run_id] = metrics

    # --- Search index operations ---
    def index_search_document(self, doc_id: str, doc: Dict[str, Any]) -> None:
        """Add or update a search document in the in-memory index."""
        self.search_index[doc_id] = doc

    def get_search_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self.search_index.get(doc_id)


# Provide a module-level client instance used by processors
data_client = InMemoryDataClient()
