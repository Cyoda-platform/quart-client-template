from unittest.mock import MagicMock, patch

from application.processors.index_for_search import handle


def test_index_for_search(monkeypatch):
    mock_client = MagicMock()
    mock_client.get_test_case.return_value = {"id":"tc1","title":"Test","description":"d","tags":[],"priority":"High"}

    with patch("application.processors.index_for_search.data_client", mock_client):
        res = handle({"test_case_id": "tc1"})

    assert res["status"] == "ok"
    assert res["indexed"] is True
