import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, request, jsonify
from quart_schema import QuartSchema, validate_request, validate_querystring

from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import entity_service, cyoda_token

app = Quart(__name__)
QuartSchema(app)

# Startup initialization for cyoda service
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Dataclass for POST /api/categories/refresh request
@dataclass
class RefreshRequest:
    forceRefresh: bool = False

# Dataclass for POST /api/categories/search request
@dataclass
class SearchRequest:
    searchTerm: str

# Workflow function to process category entity before persistence
async def process_categories_workflow(entity):
    # Example workflow: mark the entity as processed and append a workflow timestamp
    await asyncio.sleep(0.1)  # simulate async processing if needed
    entity["workflow_processed"] = True
    entity["workflow_timestamp"] = datetime.datetime.utcnow().isoformat()
    return entity

# Async function to fetch external data, transform it and store it via entity_service
async def process_categories(force_refresh: bool):
    # Fetch categories data from external API
    url = "https://api.practicesoftwaretesting.com/categories/tree"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # Basic error handling is assumed; production code should handle errors robustly.
            raw_data = await response.json()

    # Transformation logic can be added here if needed.
    transformed_data = raw_data  # Placeholder for any transformation

    # Build the data object to be stored externally
    item_data = {
        "categories": transformed_data.get("categories", []),
        "last_refresh": datetime.datetime.utcnow().isoformat()
    }
    # Store the data using external service and get the new item's id
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="categories",
        entity_version=ENTITY_VERSION,
        entity=item_data,
        workflow=process_categories_workflow  # Workflow function applied to the entity asynchronously before persistence
    )
    return new_id

# Helper function to recursively search for a category in the hierarchical tree
def search_category(tree, search_term):
    for category in tree:
        if str(category.get("id", "")).lower() == search_term.lower() or search_term.lower() in category.get("name", "").lower():
            return category
        sub_categories = category.get("subCategories", [])
        if sub_categories:
            result = search_category(sub_categories, search_term)
            if result:
                return result
    return None

# Endpoint to refresh categories data by fetching from external source and storing via entity_service
@app.route("/api/categories/refresh", methods=["POST"])
@validate_request(RefreshRequest)
async def refresh_categories(data: RefreshRequest):
    force_refresh = data.forceRefresh
    new_id = await process_categories(force_refresh)
    # Return the id of the newly stored item; retrieval is done with a separate endpoint.
    return jsonify({
        "status": "success",
        "id": new_id
    })

# Endpoint to search categories using the stored hierarchical data
@app.route("/api/categories/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_categories(data: SearchRequest):
    search_term = data.searchTerm
    if not search_term:
        return jsonify({"status": "error", "message": "searchTerm is required"}), 400

    # Retrieve all stored category items using the external entity service
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="categories",
        entity_version=ENTITY_VERSION
    )
    if not items:
        return jsonify({
            "status": "error",
            "message": "No category data available. Please refresh first."
        }), 404

    # Assume the latest stored item is the one we need for search
    latest_item = items[-1]
    tree = latest_item.get("categories", [])
    result = search_category(tree, search_term)
    if result:
        return jsonify({"status": "success", "result": result})
    else:
        return jsonify({"status": "error", "message": "Category not found"}), 404

# Endpoint to return the current categories data from the external store
@app.route("/api/categories", methods=["GET"])
async def get_categories():
    items = await entity_service.get_items(
        token=cyoda_token,
        entity_model="categories",
        entity_version=ENTITY_VERSION
    )
    if not items:
        return jsonify({
            "status": "error",
            "message": "No category data available. Please refresh first."
        }), 404

    latest_item = items[-1]
    return jsonify({
        "status": "success",
        "categories": latest_item.get("categories", []),
        "last_refresh": latest_item.get("last_refresh")
    })

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)