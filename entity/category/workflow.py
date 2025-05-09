from typing import Dict, Any
import logging
from datetime import datetime
import httpx

ENTITY_NAME = "category"
LOAD_REQUEST_ENTITY_NAME = "category_load_request"
EXTERNAL_API_URL = "https://api.practicesoftwaretesting.com/categories/tree"


async def process_add_processing_timestamp(entity_data: Dict[str, Any]):
    entity_data['processedAt'] = datetime.utcnow().isoformat()


async def process_load_category_tree(entity_data: Dict[str, Any]):
    try:
        raw_tree = await fetch_external_category_tree()
        transformed = process_transform_to_hierarchy(raw_tree)
        entity_data['categoryCache'] = transformed
        entity_data['cacheLoadedAt'] = datetime.utcnow().isoformat()
        entity_data['status'] = "category tree loaded"
    except Exception as e:
        logging.getLogger(__name__).exception("Failed to load category tree")
        entity_data['status'] = "failed to load category tree"
        entity_data['error'] = str(e)


async def process_search_categories(entity_data: Dict[str, Any]):
    # expects entity_data to have 'query' and 'searchBy'
    # ensure cache is loaded
    if 'categoryCache' not in entity_data or entity_data['categoryCache'] is None:
        try:
            raw_tree = await fetch_external_category_tree()
            transformed = process_transform_to_hierarchy(raw_tree)
            entity_data['categoryCache'] = transformed
            entity_data['cacheLoadedAt'] = datetime.utcnow().isoformat()
        except Exception as e:
            logging.getLogger(__name__).exception("Failed to load category tree during search")
            entity_data['searchResults'] = []
            entity_data['notification'] = "Failed to load category data"
            return

    query = entity_data.get('query', '')
    search_by = entity_data.get('searchBy', '')
    results = []
    if search_by == "name":
        process_find_categories_by_name(entity_data['categoryCache'], query, results)
    elif search_by == "id":
        found = process_find_category_by_id(entity_data['categoryCache'], query)
        if found:
            results.append(found)
    else:
        entity_data['searchResults'] = []
        entity_data['notification'] = "Invalid searchBy parameter"
        return

    if not results:
        entity_data['searchResults'] = []
        entity_data['notification'] = "Category not found"
    else:
        entity_data['searchResults'] = results


async def process_navigate_category(entity_data: Dict[str, Any]):
    # expects entity_data to have 'categoryId'
    if 'categoryCache' not in entity_data or entity_data['categoryCache'] is None:
        try:
            raw_tree = await fetch_external_category_tree()
            transformed = process_transform_to_hierarchy(raw_tree)
            entity_data['categoryCache'] = transformed
            entity_data['cacheLoadedAt'] = datetime.utcnow().isoformat()
        except Exception as e:
            logging.getLogger(__name__).exception("Failed to load category tree during navigate")
            entity_data['subtree'] = None
            entity_data['notification'] = "Failed to load category data"
            return

    category_id = entity_data.get('categoryId')
    if not category_id:
        entity_data['subtree'] = None
        entity_data['notification'] = "Missing categoryId"
        return

    subtree = process_find_category_by_id(entity_data['categoryCache'], category_id)
    if not subtree:
        entity_data['subtree'] = None
        entity_data['notification'] = "Category not found"
    else:
        entity_data['subtree'] = subtree


async def fetch_external_category_tree() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(EXTERNAL_API_URL, timeout=10)
        resp.raise_for_status()
        return resp.json()


def process_transform_to_hierarchy(raw_data: Any) -> Dict[str, Any]:
    # TODO: adapt if API returns flat list; here we assume it's already a tree
    return raw_data


def process_find_categories_by_name(node: Dict[str, Any], query: str, results: list):
    if query.lower() in node.get("categoryName", "").lower():
        results.append(node)
    for child in node.get("children", []):
        process_find_categories_by_name(child, query, results)


def process_find_category_by_id(node: Dict[str, Any], category_id: str) -> Any:
    if node.get("categoryId") == category_id:
        return node
    for child in node.get("children", []):
        found = process_find_category_by_id(child, category_id)
        if found:
            return found
    return None