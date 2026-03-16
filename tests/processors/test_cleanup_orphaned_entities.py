from unittest.mock import MagicMock, patch

from application.processors.cleanup_orphaned_entities import handle


def test_cleanup_requires_archived(monkeypatch):
    mock_client = MagicMock()
    with patch("application.processors.cleanup_orphaned_entities.data_client", mock_client):
        res = handle({"project_id": "p1", "from_state": "active"})
    assert res["status"] == "error"


def test_cleanup_cleans(monkeypatch):
    mock_client = MagicMock()
    mock_client.list_suites_for_project.return_value = [{"id":"s1"}]
    mock_client.list_test_runs_for_project.return_value = [{"id":"r1"}]

    with patch("application.processors.cleanup_orphaned_entities.data_client", mock_client):
        res = handle({"project_id": "p1", "from_state": "archived"})

    assert res["status"] == "ok"
    assert "s1" in res["cleaned"]["suites"]
    assert "r1" in res["cleaned"]["test_runs"]
