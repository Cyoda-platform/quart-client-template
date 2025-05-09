from dataclasses import dataclass
from typing import Optional, Dict, Any

import logging
from datetime import datetime

import httpx
from quart import Quart, jsonify
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

ENTITY_NAME = "category"
LOAD_REQUEST_ENTITY_NAME = "category_load_request"
EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/categories/tree"

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
    # Placeholder for actual transformation logic if needed
    return raw_data

async def process_category(entity_data: Dict[str, Any]) -> Dict[str, Any]:
    # Workflow for ordinary category entities: add processing timestamp
    entity_data['processedAt'] = datetime.utcnow().isoformat()
    return entity_data

async def process_category_load_request(entity_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Processing category load request...")
    try:
        raw_tree = await fetch_external_category_tree()
        transformed_tree = transform_to_hierarchy(raw_tree)
        # Persist the transformed tree as a separate entity of model 'category'
        await entity_service.add_item(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
            entity=transformed_tree,
            workflow=process_category
        )
        entity_data['status'] = 'loaded'
        entity_data['loadedAt'] = datetime.utcnow().isoformat()
        logger.info("Category tree fetched and persisted successfully.")
    except Exception as e:
        logger.error(f"Error processing category load request: {e}")
        entity_data['status'] = 'error'
        entity_data['errorMessage'] = str(e)
    return entity_data

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
@validate_request(dict)
async def load_tree(data):
    load_request_entity = {
        "requestAt": datetime.utcnow().isoformat(),
        "status": "requested"
    }
    entity_id = await entity_service.add_item(
        token=cyoda_auth_service,
        entity_model=LOAD_REQUEST_ENTITY_NAME,
        entity_version=ENTITY_VERSION,
        entity=load_request_entity,
        workflow=process_category_load_request
    )
    return jsonify({
        "status": "success",
        "message": "Category tree loading triggered.",
        "loadRequestId": entity_id
    })

@app.route("/api/categories/tree", methods=["GET"])
async def get_tree():
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"error": "Category tree not loaded"}), 404
        return jsonify({"categoryTree": items[0]})
    except Exception as e:
        logger.exception("Failed to get category tree")
        return jsonify({"error": "Failed to retrieve category tree"}), 500

@app.route("/api/categories/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_categories(data: SearchRequest):
    query = data.query
    search_by = data.searchBy
    if search_by not in ("name", "id"):
        return jsonify({"error": "Invalid searchBy value"}), 400
    try:
        items = await entity_service.get_items(
            token=cyoda_auth_service,
            entity_model=ENTITY_NAME,
            entity_version=ENTITY_VERSION,
        )
        if not items:
            return jsonify({"results": [], "notification": "Category data not loaded"}), 404
        category_tree = items[0]
    except Exception as e:
        logger.exception("Failed retrieving category data during search")
        return jsonify({"error": "Failed to retrieve category data"}), 500
    results = []
    if search_by == "name":
        find_categories_by_name(category_tree, query, results)
    else:
        found = find_category_by_id(category_tree, query)
        if found:
            results.append(found)
    if not results:
        return jsonify({"results": [], "notification": "Category not found"})
    return jsonify({"results": results})

@app.route("/api/categories/navigate", methods=["POST"])
@validate_request(NavigateRequest)
async def navigate_category(data: NavigateRequest):
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
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s - %(message)s')
    app.run(use_reloader=False, debug=True, host="0.0.0.0", port=8000, threaded=True)