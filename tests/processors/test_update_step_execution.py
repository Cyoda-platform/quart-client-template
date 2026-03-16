from unittest.mock import MagicMock, patch

from application.processors.update_step_execution import handle


def test_update_step_execution_atomic_failure(monkeypatch):
    mock_client = MagicMock()
    mock_client.get_step_execution.return_value = {"run_execution_id": "re1"}

    with patch("application.processors.update_step_execution.data_client", mock_client):
        res = handle({"step_execution_id": "se1", "new_status": "Failed"})

    assert res["status"] == "ok"
    assert res.get("atomic_failure_applied") is True
    assert res.get("updated_parent_run_execution") == "re1"
