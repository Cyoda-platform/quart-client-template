"""
Processor: index_for_search
Purpose: Index TestCase metadata into a (simulated) search index for discovery.

Behavior (stub):
- Read TestCase via data_client
- Push searchable fields to a search index (in-memory index in data_client)
- Return status
"""
from typing import Dict, Any

try:
    from application.clients.data_client import data_client
except Exception:
    data_client = None


def handle(event: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    tc_id = event.get("test_case_id")
    if not tc_id:
        return {"status": "error", "errors": ["test_case_id is required"]}

    if data_client is None:
        return {"status": "error", "errors": ["data_client not available"]}

    tc = data_client.get_test_case(tc_id)
    if not tc:
        return {"status": "error", "errors": [f"TestCase not found: {tc_id}"]}

    # Simulate indexing by adding an 'indexed' flag and search metadata to the test case
    search_doc = {
        "id": tc_id,
        "title": tc.get("title"),
        "description": tc.get("description"),
        "tags": tc.get("tags", []),
        "priority": tc.get("priority")
    }

    # Ensure data_client provides a search index method (we'll add it to in-memory client)
    try:
        data_client.index_search_document(tc_id, search_doc)
    except Exception:
        # fallback: update the test_case with indexed metadata
        data_client.update_test_case(tc_id, {"search_indexed": True, "search_doc": search_doc})

    return {"status": "ok", "indexed": True}
