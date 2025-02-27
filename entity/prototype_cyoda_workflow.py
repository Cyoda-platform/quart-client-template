import asyncio
import datetime
import aiohttp
from dataclasses import dataclass
from quart import Quart, jsonify
from quart_schema import QuartSchema, validate_request

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
# This function can be expanded to include any asynchronous tasks, enrichment,
# or secondary data retrieval/update as needed. It should only modify the entity state.
async def process_categories_workflow(entity):
    # Add a timestamp and mark the entity as processed
    entity["last_refresh"] = datetime.datetime.utcnow().isoformat()
    entity["workflow_processed"] = True
    # Additional async operations or modifications can be done here.
    await asyncio.sleep(0.1)  # simulate async processing if needed
    return entity

# Async function to fetch external data and store it via entity_service
# Logic for transforming or enriching data is delegated to the workflow function.
async def process_categories(force_refresh: bool):
    # Fetch categories data from external API
    url = "https://api.practicesoftwaretesting.com/categories/tree"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            # Basic error handling is assumed; production code should handle errors robustly.
            raw_data = await response.json()

    # Prepare the entity using raw data
    entity = {
        "categories": raw_data.get("categories", [])
    }
    # Persist the entity; the workflow function will update its state before persistence.
    new_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="categories",
        entity_version=ENTITY_VERSION,
        entity=entity,
        workflow=process_categories_workflow
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

# Endpoint to refresh categories data by fetching from external source
@app.route("/api/categories/refresh", methods=["POST"])
@validate_request(RefreshRequest)
async def refresh_categories(data: RefreshRequest):
    new_id = await process_categories(data.forceRefresh)
    # Return the id of the newly stored item; retrieval is done with a separate endpoint.
    return jsonify({
        "status": "success",
        "id": new_id
    })

# Endpoint to search categories using the stored hierarchical data
@app.route("/api/categories/search", methods=["POST"])
@validate_request(SearchRequest)
async def search_categories(data: SearchRequest):
    if not data.searchTerm:
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
    result = search_category(tree, data.searchTerm)
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