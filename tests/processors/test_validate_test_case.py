from unittest.mock import MagicMock, patch

from application.processors.validate_test_case import handle


def test_validate_test_case_missing_title(monkeypatch):
    mock_client = MagicMock()
    mock_client.get_test_case.return_value = {"id":"tc1","title":"","steps":[{"action":"","expected":""}]}

    with patch("application.processors.validate_test_case.data_client", mock_client):
        res = handle({"test_case_id": "tc1"})

    assert res["status"] == "error"
    assert "Title is required" in res["errors"]
