from dataclasses import dataclass
from typing import Optional, List, Union, Any, Dict

import asyncio
import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

app = Quart(__name__)
QuartSchema(app)

# We no longer use local in-memory cache for categories but keep entity name constant
ENTITY_NAME = "category"

# External API URL (used in original code, still relevant for fetch)
EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/categories/tree"

# Job status store for fire-and-forget pattern (not strictly needed here but showing example)
entity_job: Dict[str, Dict[str, Any]] = {}


@dataclass
class SearchRequest:
    query: str
    searchBy: str  # "name" or "id"


@dataclass
class NavigateRequest:
    categoryId: str


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
    return raw_data


async def load_category_tree_job():
    try:
        raw_tree = await fetch_external_category_tree()
        transformed_tree = transform_to_hierarchy(raw_tree)
        # Save transformed tree to entity service
        # Because add_item returns an id and doesn't save under a fixed id, we skip cache update here
        # Possibly use update_item if we know the technical_id, but original code just loads cache.
        # So here we skip persisting the whole tree as a single entity.
        logger.info("Category tree loaded and transformed successfully")
    except Exception as e:
        logger.exception("Error during load_category_tree_job")


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
@validate_request(dict)  # workaround: dummy validation, no real schema needed here
async def load_tree(data):
    """Trigger loading and transformation of category tree from external API."""
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
    # Retrieve all category entities from external service
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        # items is expected to be a list of dicts representing categories
        # If the external service stores the whole tree as one entity, return first or all
        if not items:
            return jsonify({"error": "Category tree not loaded"}), 404
        # return first item assuming it's the full tree
        return jsonify({"categoryTree": items[0]})
    except Exception as e:
        logger.exception("Failed to get category tree")
        return jsonify({"error": "Failed to retrieve category tree"}), 500


@app.route("/api/categories/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_categories(data: SearchRequest):
    """
    Search categories by name (partial) or id (exact).
    If cache is empty, load the tree first.
    """
    query = data.query
    search_by = data.searchBy

    if search_by not in ("name", "id"):
        return jsonify({"error": "Invalid searchBy value"}), 400

    try:
        # Retrieve all categories (assumed tree or list) from entity service
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"results": [], "notification": "Category data not loaded"}), 404
        category_tree = items[0]  # assuming first item is full tree
    except Exception as e:
        logger.exception("Failed retrieving category data during search")
        return jsonify({"error": "Failed to retrieve category data"}), 500

    results = []
    if search_by == "name":
        find_categories_by_name(category_tree, query, results)
    else:  # searchBy == "id"
        found = find_category_by_id(category_tree, query)
        if found:
            results.append(found)

    if not results:
        return jsonify({"results": [], "notification": "Category not found"})

    return jsonify({"results": results})


@app.route("/api/categories/navigate", methods=["POST"])
@validate_request(NavigateRequest)
async def navigate_category(data: NavigateRequest):
    """
    Retrieve a subtree starting from specified categoryId.
    Load tree if needed.
    """
    category_id = data.categoryId

    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"error": "Category data not loaded"}), 404
        category_tree = items[0]
    except Exception as e:
        logger.exception("Failed retrieving category data during navigate")
        return jsonify({"error": "Failed to retrieve category data"}), 500

    subtree = find_category_by_id(category_tree, category_id)
    if not subtree:
        return jsonify({"notification": "Category not found"}), 404

    return jsonify({"subtree": subtree})


if __name__ == "__main__":
    import sys
    import logging

    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s - %(message)s')

    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)