"""
Processor: cleanup_orphaned_entities
Purpose: When a project transitions to Deleted, remove or mark deleted all related Suites and TestRuns.

Behavior:
- Validate that the transition is allowed (only from Archived)
- Find related Suites and TestRuns for the project via data_client
- For each Suite and TestRun, perform cascading delete or mark deleted
- Return a summary of cleaned entities
"""
from typing import Dict, Any, List

try:
    from application.clients.data_client import data_client
except Exception:
    data_client = None


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    context = context or {}
    project_id = event.get("project_id")
    from_state = event.get("from_state")

    if not project_id:
        return {"status": "error", "errors": ["project_id is required"]}

    if data_client is None:
        return {"status": "error", "errors": ["data_client not available"]}

    # Enforce archive-before-delete
    if from_state != "archived":
        return {"status": "error", "errors": ["Project must be archived before deletion"]}

    cleaned = {"suites": [], "test_runs": []}

    # find suites belonging to project
    suites = data_client.list_suites_for_project(project_id)
    for s in suites:
        # perform safe delete or mark deleted
        data_client.update_suite(s.get("id"), {"deleted": True})
        cleaned["suites"].append(s.get("id"))

    # find test runs
    runs = data_client.list_test_runs_for_project(project_id)
    for r in runs:
        data_client.update_test_run(r.get("id"), {"deleted": True})
        cleaned["test_runs"].append(r.get("id"))

    # Optionally cleanup run executions and step executions via existing functions
    # for r in cleaned['test_runs']:
    #     re_list = data_client.list_test_run_executions_for_run(r)
    #     for re in re_list:
    #         data_client.update_test_run_execution(re.get('id'), {'deleted': True})

    return {"status": "ok", "cleaned": cleaned}
