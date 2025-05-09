```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# In-memory cache to mock persistence
category_cache: Optional[Dict[str, Any]] = None
category_cache_loaded_at: Optional[datetime] = None

# External API URL
EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/categories/tree"

# Job status store for fire-and-forget pattern (not strictly needed here but showing example)
entity_job: Dict[str, Dict[str, Any]] = {}


async def fetch_external_category_tree() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(EXTERNAL_API_URL, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception(f"Failed to fetch external category tree: {e}")
            raise


def transform_to_hierarchy(raw_data: Any) -> Dict[str, Any]:
    # TODO: Adapt transformation if raw API format differs
    # Assuming raw_data is already a tree-like structure matching our needs.
    # If it is a flat list, this function should convert it into a hierarchy.
    # For prototype, we pass it through.
    return raw_data


async def load_category_tree_job():
    global category_cache, category_cache_loaded_at
    try:
        raw_tree = await fetch_external_category_tree()
        transformed_tree = transform_to_hierarchy(raw_tree)
        category_cache = transformed_tree
        category_cache_loaded_at = datetime.utcnow()
        logger.info("Category tree loaded and transformed successfully")
    except Exception as e:
        logger.exception("Error during load_category_tree_job")
        # Keep old cache if loading fails


def find_categories_by_name(node: Dict[str, Any], query: str, results: list):
    if query.lower() in node.get("categoryName", "").lower():
        results.append(node)
    for child in node.get("children", []):
        find_categories_by_name(child, query, results)


def find_category_by_id(node: Dict[str, Any], category_id: str) -> Optional[Dict[str, Any]]:
    if node.get("categoryId") == category_id:
        return node
    for child in node.get("children", []):
        found = find_category_by_id(child, category_id)
        if found:
            return found
    return None


@app.route("/api/categories/load-tree", methods=["POST"])
async def load_tree():
    """Trigger loading and transformation of category tree from external API."""
    # Fire and forget task
    job_id = f"load-tree-{datetime.utcnow().isoformat()}"
    entity_job[job_id] = {"status": "processing", "requestedAt": datetime.utcnow()}
    asyncio.create_task(load_category_tree_job())
    return jsonify({
        "status": "success",
        "message": "Category tree loading started."
    })


@app.route("/api/categories/tree", methods=["GET"])
async def get_tree():
    """Return cached hierarchical category tree."""
    if category_cache is None:
        return jsonify({"error": "Category tree not loaded"}), 404
    return jsonify({"categoryTree": category_cache})


@app.route("/api/categories/search", methods=["POST"])
async def search_categories():
    """
    Search categories by name (partial) or id (exact).
    If cache is empty, load the tree first.
    """
    data = await request.get_json(force=True)
    query = data.get("query", "")
    search_by = data.get("searchBy", "")

    if not query or search_by not in ("name", "id"):
        return jsonify({"error": "Missing or invalid query/searchBy"}), 400

    # Load tree if not loaded
    if category_cache is None:
        try:
            raw_tree = await fetch_external_category_tree()
            transformed_tree = transform_to_hierarchy(raw_tree)
            global category_cache, category_cache_loaded_at
            category_cache = transformed_tree
            category_cache_loaded_at = datetime.utcnow()
        except Exception as e:
            logger.exception("Failed loading category tree during search")
            return jsonify({"error": "Failed to load category data"}), 500

    results = []
    if search_by == "name":
        find_categories_by_name(category_cache, query, results)
    else:  # searchBy == "id"
        found = find_category_by_id(category_cache, query)
        if found:
            results.append(found)

    if not results:
        return jsonify({"results": [], "notification": "Category not found"})

    return jsonify({"results": results})


@app.route("/api/categories/navigate", methods=["POST"])
async def navigate_category():
    """
    Retrieve a subtree starting from specified categoryId.
    Load tree if needed.
    """
    data = await request.get_json(force=True)
    category_id = data.get("categoryId")
    if not category_id:
        return jsonify({"error": "Missing categoryId"}), 400

    if category_cache is None:
        try:
            raw_tree = await fetch_external_category_tree()
            transformed_tree = transform_to_hierarchy(raw_tree)
            global category_cache, category_cache_loaded_at
            category_cache = transformed_tree
            category_cache_loaded_at = datetime.utcnow()
        except Exception as e:
            logger.exception("Failed loading category tree during navigate")
            return jsonify({"error": "Failed to load category data"}), 500

    subtree = find_category_by_id(category_cache, category_id)
    if not subtree:
        return jsonify({"notification": "Category not found"}), 404

    return jsonify({"subtree": subtree})


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s - %(message)s')

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)
```
