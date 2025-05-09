from dataclasses import dataclass
from typing import Optional, Dict, Any

import logging
from datetime import datetime

import httpx
from quart import Blueprint, jsonify
from quart_schema import validate_request

from app_init.app_init import BeanFactory
from common.config.config import ENTITY_VERSION

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

routes_bp = Blueprint('routes', __name__)

factory = BeanFactory(config={'CHAT_REPOSITORY': 'cyoda'})
entity_service = factory.get_services()['entity_service']
cyoda_auth_service = factory.get_services()["cyoda_auth_service"]

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

@routes_bp.route("/api/categories/load-tree", methods=["POST"])
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
        )
    return jsonify({
        "status": "success",
        "message": "Category tree loading triggered.",
        "loadRequestId": entity_id
    })

@routes_bp.route("/api/categories/tree", methods=["GET"])
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
    except Exception:
        logger.exception("Failed to get category tree")
        return jsonify({"error": "Failed to retrieve category tree"}), 500

@routes_bp.route("/api/categories/search", methods=["POST"])
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
    except Exception:
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

@routes_bp.route("/api/categories/navigate", methods=["POST"])
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
    except Exception:
        logger.exception("Failed retrieving category data during navigate")
        return jsonify({"error": "Failed to retrieve category data"}), 500
    subtree = find_category_by_id(category_tree, category_id)
    if not subtree:
        return jsonify({"notification": "Category not found"}), 404
    return jsonify({"subtree": subtree})