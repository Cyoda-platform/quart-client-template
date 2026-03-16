from unittest.mock import MagicMock, patch

from application.processors.aggregate_run_metrics import handle


def test_aggregate_run_metrics(monkeypatch):
    mock_client = MagicMock()
    mock_client.list_step_executions_for_run.return_value = [{"status":"Passed","started_at":"2026-03-16T12:45:00"},{"status":"Failed","started_at":"2026-03-16T12:46:00","finished_at":"2026-03-16T12:46:05"}]
    mock_client.upsert_execution_report.return_value = None

    with patch("application.processors.aggregate_run_metrics.data_client", mock_client):
        res = handle({"run_id": "run-1"})

    assert res["status"] == "ok"
    assert "metrics" in res
