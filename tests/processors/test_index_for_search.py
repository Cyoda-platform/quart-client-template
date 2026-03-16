from unittest.mock import MagicMock, patch

from application.processors.index_for_search import handle


def test_index_for_search(monkeypatch):
    # Use the real in-memory data client to ensure index_search_document is invoked
    from application.clients.data_client import data_client as real_client
    real_client.create_test_case("tc1", {"id":"tc1","title":"Test","description":"d","tags":[],"priority":"High"})

    res = handle({"test_case_id": "tc1"})

    assert res["status"] == "ok"
    assert res["indexed"] is True
    # verify the document exists in the in-memory search index
    doc = real_client.get_search_document("tc1")
    assert doc is not None
    assert doc["title"] == "Test"
