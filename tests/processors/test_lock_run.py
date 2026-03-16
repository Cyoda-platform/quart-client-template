from unittest.mock import MagicMock, patch

from application.processors.lock_run import handle


def test_lock_run_locks_all(monkeypatch):
    mock_client = MagicMock()
    mock_client.list_test_run_executions_for_run.return_value = [{"id":"re1"}]
    mock_client.list_step_executions_for_run_execution.return_value = [{"id":"se1"}]

    with patch("application.processors.lock_run.data_client", mock_client):
        res = handle({"run_id": "run-1"})

    assert res["status"] == "ok"
    assert res["locked"] is True
