from unittest.mock import MagicMock, patch

from application.processors.create_step_executions import handle


def test_create_step_executions_creates_steps(monkeypatch):
    mock_client = MagicMock()
    mock_client.get_test_run_execution.return_value = {"steps": [{"step_number":1, "action":"a","expected":"e"}]}
    mock_client.create_step_execution.return_value = "se1"

    with patch("application.processors.create_step_executions.data_client", mock_client):
        res = handle({"run_execution_ids": ["re1"]})

    assert res["status"] == "ok"
    assert res["created_step_executions"]["re1"] == ["se1"]
