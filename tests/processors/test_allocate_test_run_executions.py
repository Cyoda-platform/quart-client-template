from unittest.mock import MagicMock, patch

from application.processors.allocate_test_run_executions import handle


def test_allocate_creates_run_executions(monkeypatch):
    mock_client = MagicMock()
    mock_client.get_test_run.return_value = {"test_case_refs": ["tc1", "tc2"]}
    mock_client.get_test_case.side_effect = [{"title": "t1", "steps": []}, {"title": "t2", "steps": []}]
    mock_client.create_test_run_execution.side_effect = ["re1", "re2"]

    with patch("application.processors.allocate_test_run_executions.data_client", mock_client):
        res = handle({"run_id": "run-1", "created_by": "user-1"})

    assert res["status"] == "ok"
    assert "re1" in res["created_run_executions"]
